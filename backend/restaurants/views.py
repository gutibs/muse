import requests
from django.conf import settings
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
			pin_count=Count("pins"),
		).select_related("cuisine").prefetch_related("tags")

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
			qs = qs.filter(cuisine__slug=cuisine)

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
		"""
		place_id = request.data.get("placeId") or request.data.get("place_id")
		if not place_id:
			return Response({"detail": "placeId is required."}, status=status.HTTP_400_BAD_REQUEST)

		existing = Restaurant.objects.filter(google_place_id=place_id).first()
		if existing:
			serializer = self.get_serializer(self._base_queryset().get(pk=existing.pk))
			return Response(serializer.data)

		key = settings.GOOGLE_PLACES_API_KEY
		if not key:
			return Response(
				{"detail": "Google Places API is not configured."},
				status=status.HTTP_503_SERVICE_UNAVAILABLE,
			)

		fields = ",".join([
			"id",
			"displayName",
			"formattedAddress",
			"addressComponents",
			"location",
			"websiteUri",
			"internationalPhoneNumber",
			"regularOpeningHours",
			"photos",
		])
		try:
			r = requests.get(
				f"https://places.googleapis.com/v1/places/{place_id}",
				headers={
					"X-Goog-Api-Key": key,
					"X-Goog-FieldMask": fields,
				},
				timeout=5,
			)
			r.raise_for_status()
			p = r.json()
		except requests.RequestException:
			return Response(
				{"detail": "Could not verify place with Google."},
				status=status.HTTP_502_BAD_GATEWAY,
			)

		if p.get("id") != place_id:
			return Response({"detail": "Invalid placeId."}, status=status.HTTP_400_BAD_REQUEST)

		location = p.get("location") or {}
		lat = location.get("latitude")
		lng = location.get("longitude")
		if lat is None or lng is None:
			return Response(
				{"detail": "Place has no location."},
				status=status.HTTP_400_BAD_REQUEST,
			)

		city = ""
		country = ""
		for comp in p.get("addressComponents", []):
			types = comp.get("types", [])
			if "locality" in types and not city:
				city = comp.get("longText", "")
			elif "administrative_area_level_1" in types and not city:
				city = comp.get("longText", "")
			elif "country" in types:
				country = comp.get("longText", "")

		photo_url = ""
		photos = p.get("photos") or []
		if photos:
			photo_name = photos[0].get("name")
			if photo_name:
				# Absolute URL so it passes URLField validation when persisted.
				photo_url = request.build_absolute_uri(
					f"/api/v1/places/photo/?ref={photo_name}"
				)

		hours = p.get("regularOpeningHours") or {}

		restaurant = Restaurant.objects.create(
			name=(p.get("displayName") or {}).get("text", "") or "Unknown",
			location=Point(float(lng), float(lat), srid=4326),
			address=p.get("formattedAddress", ""),
			city=city,
			country=country,
			website=p.get("websiteUri", ""),
			phone=p.get("internationalPhoneNumber", ""),
			image_url=photo_url,
			opening_hours=hours.get("weekdayDescriptions", []),
			google_place_id=place_id,
			created_by=request.user,
			approval_status=Restaurant.ApprovalStatus.APPROVED,
		)
		serializer = self.get_serializer(self._base_queryset().get(pk=restaurant.pk))
		return Response(serializer.data, status=status.HTTP_201_CREATED)

class CuisineViewSet(viewsets.ReadOnlyModelViewSet):
	queryset = Cuisine.objects.all()
	serializer_class = CuisineSerializer
	pagination_class = None


class TagViewSet(viewsets.ReadOnlyModelViewSet):
	queryset = Tag.objects.all()
	serializer_class = TagSerializer
	pagination_class = None
