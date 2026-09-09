"""Bloquear y reportar (F2.B)."""

import logging

from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from rest_framework import generics, status, viewsets
from rest_framework.response import Response

from accounts.models import Block
from accounts.serializers import (
	BlockCreateSerializer,
	BlockSerializer,
	ReportSerializer,
)
from accounts.services.blocking import block_user, unblock_user
from accounts.services.reporting import create_report
from accounts.views.throttles import ReportThrottle

logger = logging.getLogger(__name__)

User = get_user_model()


class BlockViewSet(viewsets.ModelViewSet):
	"""Bloquear, desbloquear y ver a quiénes bloqueé.

	El detalle se direcciona por el **id del usuario bloqueado**, no por el id
	de la fila: quien desbloquea conoce a la persona, no el número de su
	bloqueo.
	"""

	serializer_class = BlockSerializer
	http_method_names = ["get", "post", "delete"]
	pagination_class = None
	lookup_field = "blocked_id"
	# Sin esto el router acepta `[^/.]+` y un DELETE /blocks/abc/ llega al ORM
	# como pk no numérica: ValueError, o sea 500.
	lookup_value_regex = "[0-9]+"

	def get_queryset(self):
		# Sólo los bloqueos que hice yo. Devolver los recibidos le diría al
		# bloqueado que lo bloquearon (RF2).
		return Block.objects.filter(blocker=self.request.user).select_related("blocked__profile")

	def create(self, request, *args, **kwargs):
		# Validado y no pasado crudo a get_object_or_404: ése sólo atrapa
		# DoesNotExist, así que un "abc" reventaba con ValueError → 500 en un
		# endpoint público.
		serializer = BlockCreateSerializer(data=request.data)
		serializer.is_valid(raise_exception=True)
		target = serializer.validated_data["user_id"]
		block = block_user(blocker=request.user, blocked=target)
		return Response(self.get_serializer(block).data, status=status.HTTP_200_OK)

	def destroy(self, request, *args, **kwargs):
		target = get_object_or_404(User, pk=kwargs[self.lookup_field])
		unblock_user(blocker=request.user, blocked=target)
		return Response(status=status.HTTP_204_NO_CONTENT)


class ReportCreateView(generics.CreateAPIView):
	"""Sólo POST. No hay listado: al reportado no se le dice nunca que lo
	reportaron (RF20), y quien reporta tampoco necesita ver su historial —el
	seguimiento lo hace el moderador en el admin."""

	serializer_class = ReportSerializer
	throttle_classes = (ReportThrottle,)

	def create(self, request, *args, **kwargs):
		serializer = self.get_serializer(data=request.data)
		serializer.is_valid(raise_exception=True)
		report = create_report(
			reporter=request.user,
			reported_user=serializer.validated_data["reported_user"],
			pin=serializer.validated_data.get("pin"),
			reason=serializer.validated_data["reason"],
			detail=serializer.validated_data.get("detail", ""),
		)
		return Response(self.get_serializer(report).data, status=status.HTTP_201_CREATED)
