from django.db import IntegrityError, transaction
from rest_framework import generics, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle

from pins.models import Pin, SharedList
from pins.selectors import visible_pins
from pins.serializers import (
	PinSerializer,
	SharedListSerializer,
)
from pins.serializers_public import SharedListPublicSerializer


class PinViewSet(viewsets.ModelViewSet):
	serializer_class = PinSerializer

	def get_queryset(self):
		# Filters are applied for any action (list/retrieve/etc); for retrieve
		# the per-pk lookup short-circuits these, so there's no behavior change
		# for non-list calls. `?status=all` is treated as "no filter" so the
		# frontend can pass it explicitly without a separate code path.
		params = self.request.query_params
		return visible_pins(
			self.request.user,
			status=params.get("status"),
			tag=params.get("tag"),
			city=params.get("city"),
			favourite=params.get("favourite") in ("true", "1"),
		)

	@action(detail=True, methods=["post"])
	def favourite(self, request, pk=None):
		"""Marca o desmarca el pin como favorito.

		Tiene acción propia en vez de ir por PATCH porque se escribe con
		`.update()`, que no dispara `auto_now`: con
		`Pin.Meta.ordering = ["-updated_at"]`, un PATCH mandaría el pin al
		tope de la lista y la lista saltaría bajo el dedo de quien tocó la
		estrella.

		`get_queryset` ya filtra por usuario, así que el pin de otra persona
		devuelve 404 sin un chequeo extra.
		"""
		pin = self.get_object()
		valor = request.data.get("isFavourite", request.data.get("is_favourite"))
		if not isinstance(valor, bool):
			return Response(
				{"detail": "isFavourite must be a boolean."},
				status=status.HTTP_400_BAD_REQUEST,
			)

		Pin.objects.filter(pk=pin.pk).update(is_favourite=valor)
		return Response({"id": pin.pk, "isFavourite": valor})

	def create(self, request, *args, **kwargs):
		# (user, restaurant) is unique. If a pin already exists, surface that as
		# 409 with the existing pin id so the client can navigate the user
		# straight to the edit screen instead of showing a generic 500.
		#
		# The atomic() block is required, not decorative: in PostgreSQL a failed
		# statement aborts the surrounding transaction, so without a savepoint
		# to roll back to, the lookup below raises TransactionManagementError
		# instead of returning the pin. Harmless under autocommit, fatal the day
		# a request runs inside a transaction (ATOMIC_REQUESTS, a wrapping
		# atomic block, or a test).
		try:
			with transaction.atomic():
				return super().create(request, *args, **kwargs)
		except IntegrityError:
			restaurant_id = request.data.get("restaurant") or request.data.get("restaurantId")
			existing = Pin.objects.filter(user=request.user, restaurant_id=restaurant_id).first()
			payload = {"detail": "You already pinned this restaurant."}
			if existing:
				payload["pinId"] = existing.id
			return Response(payload, status=status.HTTP_409_CONFLICT)


class SharedListViewSet(viewsets.ModelViewSet):
	serializer_class = SharedListSerializer
	http_method_names = ["get", "post", "patch", "delete"]

	def get_queryset(self):
		return SharedList.objects.filter(user=self.request.user)


class SharedListPublicView(generics.RetrieveAPIView):
	serializer_class = SharedListPublicSerializer
	permission_classes = (permissions.AllowAny,)
	authentication_classes = ()
	# Its own scope: this used to fall back to the global anonymous throttle,
	# which is shared with every other unauthenticated surface. A share link
	# posted in a group chat is legitimately hit by many people at once, so it
	# needs a limit of its own rather than borrowing someone else's.
	throttle_classes = (ScopedRateThrottle,)
	throttle_scope = "shared_list_public"
	lookup_field = "token"

	def get_queryset(self):
		# Una lista vencida es un 404, igual que una desactivada: quien tiene
		# el link no tiene por qué saber si existió.
		from django.db.models import Q
		from django.utils import timezone

		return (
			SharedList.objects.filter(is_active=True)
			.filter(Q(expires_at__isnull=True) | Q(expires_at__gt=timezone.now()))
			.select_related("user__profile")
			.prefetch_related("items__pin__restaurant")
		)
