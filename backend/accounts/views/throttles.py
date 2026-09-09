"""Los límites por scope de `accounts`.

Las rates viven en `settings.REST_FRAMEWORK`; acá sólo está a qué scope
pertenece cada endpoint. `ClientIPRateThrottle` cuenta por IP y no por usuario
porque los endpoints que la usan son anónimos por definición.
"""

import logging

from django.contrib.auth import get_user_model
from rest_framework.throttling import AnonRateThrottle, SimpleRateThrottle, UserRateThrottle

logger = logging.getLogger(__name__)

User = get_user_model()


class LoginAnonThrottle(AnonRateThrottle):
	scope = "login"


class LoginUserThrottle(UserRateThrottle):
	scope = "login"


class RegisterAnonThrottle(AnonRateThrottle):
	scope = "register"


class UserSearchThrottle(UserRateThrottle):
	scope = "user_search"


class InviteThrottle(UserRateThrottle):
	scope = "invite"


class FriendCodeThrottle(UserRateThrottle):
	scope = "friend_code"


class ClientIPRateThrottle(SimpleRateThrottle):
	"""Cuenta por IP de cliente SIEMPRE, tenga sesión o no.

	`AnonRateThrottle.get_cache_key` devuelve None cuando el request viene
	autenticado, o sea que no cuenta nada. En un endpoint `AllowAny` eso es un
	agujero: el registro es abierto, así que una cuenta gratis se saltea el
	tope entero. En estos dos endpoints el tope no protege sólo la cuenta —
	cada pedido cuesta un email real que sale de nuestro dominio— así que
	tiene que valer también para quien viene con token.

	La identidad sale de `get_ident`, que depende de NUM_PROXIES (RF14).
	"""

	def get_cache_key(self, request, view):
		return self.cache_format % {"scope": self.scope, "ident": self.get_ident(request)}


class PasswordResetThrottle(ClientIPRateThrottle):
	scope = "password_reset"


class PasswordResetConfirmThrottle(ClientIPRateThrottle):
	scope = "password_reset_confirm"


class ReportThrottle(UserRateThrottle):
	"""Por usuario y no por IP: el endpoint es autenticado, así que se puede
	identificar al que abusa. Contando por IP, un abusador detrás de un NAT
	—wifi de oficina, CGNAT de una operadora— le agota el cupo a todos los que
	comparten esa salida, y reportar es justamente la capacidad que la
	guideline exige que funcione."""

	scope = "report"
