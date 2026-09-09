"""Entrar, salir y recuperar la cuenta.

`PasswordResetView` contesta lo mismo exista o no la cuenta: el endpoint es
anónimo y cualquier diferencia lo convierte en un oráculo de emails
registrados.
"""

import logging

from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from rest_framework import generics, permissions, status, views
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.serializers import (
	ChangePasswordSerializer,
	PasswordResetConfirmSerializer,
	PasswordResetRequestSerializer,
	RegisterSerializer,
)
from accounts.services.consent import client_ip, pending_policies, record_consent
from accounts.services.password_reset import confirm_reset, request_reset
from accounts.views.throttles import (
	PasswordResetConfirmThrottle,
	PasswordResetThrottle,
	RegisterAnonThrottle,
)

logger = logging.getLogger(__name__)

User = get_user_model()


# El cuerpo es literalmente el mismo objeto para todos los caminos de
# PasswordResetView: exista la cuenta, no exista, o falle Resend (RF2). Si
# alguna vez hay que tocarlo, se toca acá y sigue siendo uno solo.
PASSWORD_RESET_ACCEPTED = {
	"detail": _("If an account exists for that email, a code has been sent.")
}


class RegisterView(generics.CreateAPIView):
	serializer_class = RegisterSerializer
	permission_classes = (permissions.AllowAny,)
	throttle_classes = (RegisterAnonThrottle,)

	def create(self, request, *args, **kwargs):
		serializer = self.get_serializer(data=request.data)
		serializer.is_valid(raise_exception=True)
		result = serializer.save()
		# 202 y no 201: la respuesta es la misma exista o no la cuenta, así que
		# no puede afirmar que se creó algo. El alta no devuelve sesión —ver el
		# docstring del serializer— y se entra por el login de siempre.
		return Response(result, status=status.HTTP_202_ACCEPTED)


class ConsentView(views.APIView):
	"""Deja constancia de que esta persona aceptó los documentos legales que le faltaban.

	Existe por las cuentas anteriores al registro de consentimientos: la
	migración que creó la tabla fue schema-only, así que 16 de los 17 perfiles
	de producción no tienen ninguna fila y no hay forma de demostrar qué
	aceptaron. La app las frena con `pendingPolicies` y las manda acá.

	Idempotente: sin nada pendiente responde una lista vacía en vez de fallar,
	porque el cliente puede reintentar y no tiene por qué saber qué le falta.

	**El bloqueo vive en la app y no acá, a propósito.** Ninguna permission
	class rechaza a una cuenta con políticas pendientes, así que un APK viejo o
	un cliente propio siguen operando sin haber aceptado. Enforzarlo del lado
	del servidor dejaría a quien tiene una versión anterior con todas las
	llamadas en 403 y sin ninguna pantalla que le explique por qué —su APK no
	trae el gate—, que es la pantalla sin salida que F2.H se ocupó de evitar
	fallando abierto. El afectado por no enforzarlo es el responsable del
	tratamiento, no otro usuario.
	"""

	def post(self, request):
		registradas = record_consent(
			request.user,
			pending_policies(request.user),
			ip_address=client_ip(request),
		)
		return Response({"accepted": [c.policy for c in registradas]})


class ChangePasswordView(generics.GenericAPIView):
	"""Cambiar la contraseña estando adentro.

	Devuelve un par de tokens nuevo, y no un 204. Con CHECK_REVOKE_TOKEN, el
	cambio de contraseña invalida todo lo firmado con el hash anterior — que
	incluye el token del dispositivo desde el que estás cambiándola. Sin el par
	nuevo, el usuario ve "contraseña actualizada" y la llamada siguiente lo
	manda al login sin explicación. Las OTRAS sesiones sí se cierran, que es lo
	que se busca.
	"""

	serializer_class = ChangePasswordSerializer

	def post(self, request):
		serializer = self.get_serializer(data=request.data)
		serializer.is_valid(raise_exception=True)
		request.user.set_password(serializer.validated_data["new_password"])
		request.user.save()
		refresh = RefreshToken.for_user(request.user)
		return Response(
			{"refresh": str(refresh), "access": str(refresh.access_token)},
			status=status.HTTP_200_OK,
		)


class PasswordResetView(generics.GenericAPIView):
	"""Pide un código de recuperación. Endpoint anónimo.

	Responde 200 con el mismo cuerpo siempre (RF2). Cualquier excepción que
	se escapara de acá sería un oráculo de enumeración, así que el service no
	levanta nada y esta vista no tiene ramas.
	"""

	serializer_class = PasswordResetRequestSerializer
	permission_classes = (permissions.AllowAny,)
	throttle_classes = (PasswordResetThrottle,)

	def post(self, request):
		serializer = self.get_serializer(data=request.data)
		serializer.is_valid(raise_exception=True)
		request_reset(
			email=serializer.validated_data["email"],
			language=serializer.validated_data.get("language"),
		)
		return Response(PASSWORD_RESET_ACCEPTED, status=status.HTTP_200_OK)


class PasswordResetConfirmView(generics.GenericAPIView):
	"""Canjea el código por una contraseña nueva. Endpoint anónimo.

	El 400 sale del ValidationError que levanta el service, con el mismo
	mensaje para código errado, vencido, quemado o usado.
	"""

	serializer_class = PasswordResetConfirmSerializer
	permission_classes = (permissions.AllowAny,)
	throttle_classes = (PasswordResetConfirmThrottle,)

	def post(self, request):
		serializer = self.get_serializer(data=request.data)
		serializer.is_valid(raise_exception=True)
		confirm_reset(
			email=serializer.validated_data["email"],
			code=serializer.validated_data["code"],
			new_password=serializer.validated_data["new_password"],
			language=serializer.validated_data.get("language"),
		)
		return Response({"detail": _("Password updated.")}, status=status.HTTP_200_OK)
