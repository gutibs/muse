"""Registro y baja del dispositivo.

Es todo lo que la app necesita del lado del servidor: las preferencias viajan
por el perfil, que ya existe.
"""

import logging

from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from notifications.models import DeviceToken
from notifications.serializers import DeviceTokenSerializer

logger = logging.getLogger(__name__)


class DeviceTokenView(APIView):
	permission_classes = (permissions.IsAuthenticated,)

	def post(self, request):
		"""Registra el token de este dispositivo. Idempotente.

		`update_or_create` sobre el token —que es único a nivel tabla— es lo
		que hace que un teléfono con dos cuentas no le siga mandando
		notificaciones a la primera: la fila cambia de dueño en lugar de
		duplicarse.
		"""
		serializer = DeviceTokenSerializer(data=request.data)
		serializer.is_valid(raise_exception=True)

		DeviceToken.objects.update_or_create(
			token=serializer.validated_data["token"],
			defaults={
				"user": request.user,
				"platform": serializer.validated_data.get("platform", DeviceToken.Platform.ANDROID),
			},
		)
		_enforce_device_cap(request.user)
		# Sin `detail`: no hay nada que mostrarle a nadie acá, y un literal en
		# esa clave lo marca —con razón— el guardián de i18n.
		return Response({"registered": True}, status=status.HTTP_200_OK)

	def delete(self, request):
		"""Baja el token al cerrar sesión."""
		token = request.data.get("token", "")
		if token:
			DeviceToken.objects.filter(user=request.user, token=token).delete()
		return Response(status=status.HTTP_204_NO_CONTENT)


def _enforce_device_cap(user):
	"""Deja los N más recientes. El teléfono viejo deja de recibir solo."""
	extra = list(
		DeviceToken.objects.filter(user=user)
		.order_by("-last_seen_at")
		.values_list("pk", flat=True)[DeviceToken.MAX_PER_USER :]
	)
	if extra:
		DeviceToken.objects.filter(pk__in=extra).delete()
		logger.info("device cap: %d token(s) viejos borrados para %s", len(extra), user.pk)
