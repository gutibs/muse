import logging

from django.contrib.gis.db.models.functions import Distance
from django.contrib.gis.geos import Point
from django.db.models import Avg, Count
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from places.geo import KM_PER_DEGREE, parse_lat_lng, parse_radius_km
from restaurants.filters import RestaurantFilterSet
from restaurants.models import Cuisine, Restaurant, Tag
from restaurants.serializers import (
	CuisineSerializer,
	RestaurantDetailSerializer,
	RestaurantSerializer,
	TagSerializer,
)
from restaurants.services.google_import import (
	GoogleImportError,
	import_from_google_place_id,
)

logger = logging.getLogger(__name__)


class RestaurantViewSet(viewsets.ModelViewSet):
	serializer_class = RestaurantSerializer
	http_method_names = ["get", "post", "patch"]
	filterset_class = RestaurantFilterSet

	def get_serializer_class(self):
		if self.action == "retrieve":
			return RestaurantDetailSerializer
		return RestaurantSerializer

	def _base_queryset(self):
		return (
			Restaurant.objects.annotate(
				average_rating=Avg("pins__rating"),
				pin_count=Count("pins", distinct=True),
			)
			.prefetch_related("cuisines", "tags")
			# Explicit, and not redundant with Meta.ordering: Django drops the
			# model's default ordering on any queryset with an aggregate
			# annotation, because those columns would have to join the GROUP BY.
			# Without this the list endpoint paginates an unordered queryset and
			# rows can repeat across pages or vanish. Verified in the generated
			# SQL — the annotated query came out with no ORDER BY at all.
			.order_by("name", "id")
		)

	def get_queryset(self):
		qs = self._base_queryset()
		# Admins see everything, regular users only see approved
		if not (self.request.user.is_staff or self.request.user.is_superuser):
			qs = qs.filter(approval_status=Restaurant.ApprovalStatus.APPROVED)
			# Los cerrados se ocultan acá y no en `_base_queryset`, del que
			# cuelga `retrieve`: la ficha tiene que seguir respondiendo para
			# que el pin de alguien no se convierta en un 404.
			qs = qs.filter(is_closed=False)
		return qs

	# `list` is no longer overridden: the default ModelViewSet implementation
	# runs filter_queryset() and paginates, which is exactly what the hand-rolled
	# version did minus the filtering. Filters live in RestaurantFilterSet.

	def create(self, request, *args, **kwargs):
		"""Users suggest a restaurant; it starts as 'pending' until admin approves."""
		serializer = self.get_serializer(data=request.data)
		serializer.is_valid(raise_exception=True)
		serializer.save()
		return Response(serializer.data, status=status.HTTP_201_CREATED)

	def _check_owner_or_staff(self, instance, request):
		if instance.created_by_id != request.user.id and not (
			request.user.is_staff or request.user.is_superuser
		):
			raise PermissionDenied("You cannot modify restaurants you did not create.")

	def update(self, request, *args, **kwargs):
		instance = self.get_object()
		self._check_owner_or_staff(instance, request)
		return super().update(request, *args, **kwargs)

	def partial_update(self, request, *args, **kwargs):
		instance = self.get_object()
		self._check_owner_or_staff(instance, request)
		return super().partial_update(request, *args, **kwargs)

	def retrieve(self, request, *args, **kwargs):
		"""Allow retrieving a specific restaurant even if pending (for the user who created it)."""
		instance = self._base_queryset().filter(pk=self.kwargs["pk"]).first()
		if not instance:
			return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
		# Non-staff can only see approved OR their own pending
		if (
			instance.approval_status != Restaurant.ApprovalStatus.APPROVED
			and not (request.user.is_staff or request.user.is_superuser)
			and instance.created_by != request.user
		):
			return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
		serializer = self.get_serializer(instance)
		return Response(serializer.data)

	@action(detail=False, methods=["get"])
	def nearby(self, request):
		# Parsing lives in places.geo so this endpoint and the reverse-geocode
		# proxy validate coordinates the same way. Bad input raises DRF's
		# ValidationError → 400; it used to reach a bare float() and 500.
		lat, lng = parse_lat_lng(request.query_params)
		radius_km = parse_radius_km(request.query_params)

		point = Point(lng, lat, srid=4326)
		# Through filter_queryset so "near me" can be combined with the same
		# filters as the list endpoint — it used to take the bare queryset, so
		# any ?cuisine= or ?search= alongside ?lat= was silently ignored.
		# Filtering happens before the [:50] slice, not after: otherwise the
		# answer is "of the 50 nearest, the ones that match", which is not what
		# anyone means by it.
		qs = (
			self.filter_queryset(self.get_queryset())
			.filter(location__dwithin=(point, radius_km / KM_PER_DEGREE))
			.annotate(distance=Distance("location", point))
			.order_by("distance")
		)
		serializer = self.get_serializer(qs[:50], many=True)
		return Response(serializer.data)

	@action(detail=False, methods=["post"])
	def from_google(self, request):
		"""Find or create a Restaurant from a Google placeId.

		Only `placeId` is trusted from the client. All restaurant fields are
		re-fetched from Google Places API before creating the record so the
		client cannot spoof name/address/coords and bypass admin approval.

		The fetch + parse + race-safe persistence lives in
		`restaurants.services.google_import` so this view stays a thin
		HTTP boundary.
		"""
		place_id = request.data.get("placeId") or request.data.get("place_id")
		if not place_id:
			return Response({"detail": "placeId is required."}, status=status.HTTP_400_BAD_REQUEST)

		try:
			restaurant, created = import_from_google_place_id(place_id, request.user)
		except GoogleImportError as exc:
			return Response({"detail": exc.message}, status=exc.status_code)

		if restaurant.is_closed:
			# El importador devuelve la fila existente sin volver a mirar
			# Google, así que sin este corte un lugar cerrado se traía de
			# vuelta desde el autocomplete y se pineaba como si nada.
			return Response(
				{
					"detail": "This place is permanently closed.",
					"restaurantId": restaurant.id,
				},
				status=status.HTTP_409_CONFLICT,
			)

		serializer = self.get_serializer(self._base_queryset().get(pk=restaurant.pk))
		http_status = status.HTTP_201_CREATED if created else status.HTTP_200_OK
		return Response(serializer.data, status=http_status)


class CuisineViewSet(viewsets.ReadOnlyModelViewSet):
	queryset = Cuisine.objects.all()
	serializer_class = CuisineSerializer
	pagination_class = None


class TagViewSet(viewsets.ReadOnlyModelViewSet):
	"""Catálogo de etiquetas, opcionalmente acotado a un eje con `?kind=`.

	Sin el filtro, la pantalla de "vibe" ofrecía `vegetarian` y `gluten-free`,
	que son dietary: el endpoint devolvía la tabla entera y el cliente no
	tenía con qué separarlas.
	"""

	serializer_class = TagSerializer
	pagination_class = None

	def get_queryset(self):
		qs = Tag.objects.all()
		kind = self.request.query_params.get("kind")
		if kind in Tag.Kind.values:
			qs = qs.filter(kind=kind)
		return qs
