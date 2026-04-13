from django.contrib.gis.db.models.functions import Distance
from django.contrib.gis.geos import Point
from django.db.models import Avg, Count
from rest_framework import status, viewsets
from rest_framework.decorators import action
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

	@action(detail=False, methods=["get"])
	def my_suggestions(self, request):
		"""List restaurants the current user has suggested (pending/rejected)."""
		qs = (
			self._base_queryset()
			.filter(created_by=request.user)
			.exclude(approval_status=Restaurant.ApprovalStatus.APPROVED)
		)
		serializer = self.get_serializer(qs, many=True)
		return Response(serializer.data)


class CuisineViewSet(viewsets.ReadOnlyModelViewSet):
	queryset = Cuisine.objects.all()
	serializer_class = CuisineSerializer
	pagination_class = None


class TagViewSet(viewsets.ReadOnlyModelViewSet):
	queryset = Tag.objects.all()
	serializer_class = TagSerializer
	pagination_class = None
