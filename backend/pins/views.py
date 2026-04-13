from rest_framework import generics, permissions, viewsets
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
		return (
			Pin.objects.filter(user=self.request.user)
			.select_related("restaurant", "restaurant__cuisine")
			.prefetch_related("personas")
		)

	def list(self, request, *args, **kwargs):
		qs = self.get_queryset()
		status = request.query_params.get("status")
		persona = request.query_params.get("persona")
		city = request.query_params.get("city")

		if status:
			qs = qs.filter(status=status)
		if persona:
			qs = qs.filter(personas__slug=persona)
		if city:
			qs = qs.filter(restaurant__city__icontains=city)

		page = self.paginate_queryset(qs)
		if page is not None:
			serializer = self.get_serializer(page, many=True)
			return self.get_paginated_response(serializer.data)
		serializer = self.get_serializer(qs, many=True)
		return Response(serializer.data)


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
