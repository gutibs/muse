import logging

from django.contrib.gis.db.models.functions import Distance
from django.contrib.gis.geos import Point
from django.db.models import Avg, Count
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

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

	def get_serializer_class(self):
		if self.action == "retrieve":
			return RestaurantDetailSerializer
		return RestaurantSerializer

	def _base_queryset(self):
		return Restaurant.objects.annotate(
			average_rating=Avg("pins__rating"),
			pin_count=Count("pins", distinct=True),
		).prefetch_related("cuisines", "tags")

	def get_queryset(self):
		qs = self._base_queryset()
		# Admins see everything, regular users only see approved
		if not (self.request.user.is_staff or self.request.user.is_superuser):
			qs = qs.filter(approval_status=Restaurant.ApprovalStatus.APPROVED)
		return qs

	def get_queryset_filtered(self):
		qs = self.get_queryset()
		search = self.request.query_params.get("search")
		city = self.request.query_params.get("city")
		cuisine = self.request.query_params.get("cuisine")

		if search:
			qs = qs.filter(name__icontains=search)
		if city:
			qs = qs.filter(city__icontains=city)
		if cuisine:
			# Comma-separated slugs → match restaurants with ANY of them.
			slugs = [s.strip() for s in cuisine.split(",") if s.strip()]
			if slugs:
				qs = qs.filter(cuisines__slug__in=slugs).distinct()

		return qs

	def list(self, request, *args, **kwargs):
		queryset = self.get_queryset_filtered()
		page = self.paginate_queryset(queryset)
		if page is not None:
			serializer = self.get_serializer(page, many=True)
			return self.get_paginated_response(serializer.data)
		serializer = self.get_serializer(queryset, many=True)
		return Response(serializer.data)

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
		lat = request.query_params.get("lat")
		lng = request.query_params.get("lng")
		radius = float(request.query_params.get("radius", 5))

		if not lat or not lng:
			return Response(
				{"detail": "lat and lng are required."},
				status=status.HTTP_400_BAD_REQUEST,
			)

		point = Point(float(lng), float(lat), srid=4326)
		qs = (
			self.get_queryset()
			.filter(location__dwithin=(point, radius / 111.32))
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

		def photo_url_for(name: str) -> str:
			# Absolute URL so it passes URLField validation when persisted.
			# Stays in the view because it depends on the request host.
			return request.build_absolute_uri(f"/api/v1/places/photo/?ref={name}")

		try:
			restaurant, created = import_from_google_place_id(
				place_id, request.user, photo_url_builder=photo_url_for
			)
		except GoogleImportError as exc:
			return Response({"detail": exc.message}, status=exc.status_code)

		serializer = self.get_serializer(self._base_queryset().get(pk=restaurant.pk))
		http_status = status.HTTP_201_CREATED if created else status.HTTP_200_OK
		return Response(serializer.data, status=http_status)


class CuisineViewSet(viewsets.ReadOnlyModelViewSet):
	queryset = Cuisine.objects.all()
	serializer_class = CuisineSerializer
	pagination_class = None


class TagViewSet(viewsets.ReadOnlyModelViewSet):
	queryset = Tag.objects.all()
	serializer_class = TagSerializer
	pagination_class = None
