import logging

from django.contrib.auth import get_user_model
from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.exceptions import InvalidToken
from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.utils import get_md5_hash_password
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from accounts.views import (
	BlockViewSet,
	ChangePasswordView,
	DietaryPreferenceListView,
	EmailInvitationView,
	FriendshipViewSet,
	LoginAnonThrottle,
	LoginUserThrottle,
	PasswordResetConfirmView,
	PasswordResetView,
	ProfileView,
	PublicProfileView,
	RegisterView,
	UserPinsView,
	UserSearchView,
)

logger = logging.getLogger(__name__)


class ThrottledTokenObtainPairView(TokenObtainPairView):
	throttle_classes = (LoginAnonThrottle, LoginUserThrottle)


class ThrottledTokenRefreshView(TokenRefreshView):
	"""Refresh con la revocación de simplejwt aplicada de verdad.

	`CHECK_REVOKE_TOKEN` se chequea sólo en `JWTAuthentication.get_user`, así
	que sin esto un refresh emitido antes de un reset de contraseña sigue
	siendo aceptado acá: devuelve 200 y —con ROTATE_REFRESH_TOKENS— otro
	refresh, indefinidamente. Los access que produce no autentican (heredan el
	claim viejo), pero RF13 dice que nada emitido antes del reset sobrevive, y
	un refresh robado que nunca muere no cumple eso.
	"""

	throttle_classes = (LoginAnonThrottle, LoginUserThrottle)

	def post(self, request, *args, **kwargs):
		if api_settings.CHECK_REVOKE_TOKEN:
			self._reject_if_revoked(request.data.get("refresh"))
		return super().post(request, *args, **kwargs)

	@staticmethod
	def _reject_if_revoked(raw_refresh):
		if not raw_refresh:
			return
		try:
			token = RefreshToken(raw_refresh)
		except Exception as exc:
			# Token inválido o vencido: que conteste el serializer de
			# simplejwt, que ya devuelve el 401 con su mensaje.
			logger.debug("Refresh token unparseable before revoke check: %s", exc)
			return
		user_id = token.payload.get(api_settings.USER_ID_CLAIM)
		user = get_user_model().objects.filter(**{api_settings.USER_ID_FIELD: user_id}).first()
		if user is None:
			return
		if token.payload.get(api_settings.REVOKE_TOKEN_CLAIM) != get_md5_hash_password(
			user.password
		):
			raise InvalidToken("The user's password has been changed.")


router = DefaultRouter()
router.register("friendships", FriendshipViewSet, basename="friendship")
router.register("blocks", BlockViewSet, basename="block")

urlpatterns = [
	path("register/", RegisterView.as_view(), name="register"),
	path("token/", ThrottledTokenObtainPairView.as_view(), name="token_obtain"),
	path("token/refresh/", ThrottledTokenRefreshView.as_view(), name="token_refresh"),
	path("profile/", ProfileView.as_view(), name="profile"),
	path("dietary-preferences/", DietaryPreferenceListView.as_view(), name="dietary_preferences"),
	path("change-password/", ChangePasswordView.as_view(), name="change_password"),
	path("password-reset/", PasswordResetView.as_view(), name="password_reset"),
	path(
		"password-reset/confirm/",
		PasswordResetConfirmView.as_view(),
		name="password_reset_confirm",
	),
	path("search/", UserSearchView.as_view(), name="user_search"),
	path("invite/", EmailInvitationView.as_view(), name="email_invite"),
	path("users/<int:user_id>/", PublicProfileView.as_view(), name="public_profile"),
	path("users/<int:user_id>/pins/", UserPinsView.as_view(), name="user_pins"),
	path("", include(router.urls)),
]
