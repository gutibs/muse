from django.db import IntegrityError
from rest_framework import generics, permissions, status, viewsets
from rest_framework.response import Response

from pins.models import Persona, Pin, SharedList
from pins.serializers import (
	PersonaSerializer,
	PinSerializer,
	SharedListPublicSerializer,
	SharedListSerializer,
)


class PinViewSet(viewsets.ModelViewSet):
	serializer_class = PinSerializer

	def get_queryset(self):
		qs = (
			Pin.objects.filter(user=self.request.user)
			.select_related("restaurant")
			.prefetch_related("personas", "restaurant__cuisines")
		)
		# Filters are applied for any action (list/retrieve/etc); for retrieve
		# the per-pk lookup short-circuits these, so there's no behavior change
		# for non-list calls. `?status=all` is treated as "no filter" so the
		# frontend can pass it explicitly without a separate code path.
		status_filter = self.request.query_params.get("status")
		persona = self.request.query_params.get("persona")
		city = self.request.query_params.get("city")

		if status_filter and status_filter != "all":
			qs = qs.filter(status=status_filter)
		if persona:
			qs = qs.filter(personas__slug=persona)
		if city:
			qs = qs.filter(restaurant__city__icontains=city)
		return qs

	def create(self, request, *args, **kwargs):
		# (user, restaurant) is unique. If a pin already exists, surface that as
		# 409 with the existing pin id so the client can navigate the user
		# straight to the edit screen instead of showing a generic 500.
		try:
			return super().create(request, *args, **kwargs)
		except IntegrityError:
			restaurant_id = request.data.get("restaurant") or request.data.get("restaurantId")
			existing = Pin.objects.filter(user=request.user, restaurant_id=restaurant_id).first()
			payload = {"detail": "You already pinned this restaurant."}
			if existing:
				payload["pinId"] = existing.id
			return Response(payload, status=status.HTTP_409_CONFLICT)


class PersonaViewSet(viewsets.ReadOnlyModelViewSet):
	queryset = Persona.objects.all()
	serializer_class = PersonaSerializer
	pagination_class = None


class SharedListViewSet(viewsets.ModelViewSet):
	serializer_class = SharedListSerializer
	http_method_names = ["get", "post", "patch", "delete"]

	def get_queryset(self):
		return SharedList.objects.filter(user=self.request.user)


class SharedListPublicView(generics.RetrieveAPIView):
	serializer_class = SharedListPublicSerializer
	permission_classes = (permissions.AllowAny,)
	authentication_classes = ()
	lookup_field = "token"

	def get_queryset(self):
		return SharedList.objects.filter(is_active=True).select_related("user__profile")
