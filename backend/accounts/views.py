import logging

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle, SimpleRateThrottle, UserRateThrottle
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.models import DietaryPreference, EmailInvitation, Friendship
from accounts.serializers import (
	AccountDeletionSerializer,
	ChangePasswordSerializer,
	DietaryPreferenceSerializer,
	EmailInvitationSerializer,
	FriendshipSerializer,
	PasswordResetConfirmSerializer,
	PasswordResetRequestSerializer,
	ProfileSerializer,
	RegisterSerializer,
	UserPublicSerializer,
)
from accounts.services.account_deletion import anonymise_user
from accounts.services.email import EmailSendError, send_invitation_email
from accounts.services.friendships import are_friends
from accounts.services.password_reset import confirm_reset, request_reset
from accounts.services.visibility import require_can_view
from pins.selectors import visible_pins
from pins.serializers import PinSerializer

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


# Kept as a module-level alias for the tests that still import it from here.
# The implementation lives in accounts.services.friendships, next to
# friend_ids(); the views themselves now go through
# accounts.services.visibility, which answers the policy question rather than
# the question of fact.
_are_friends = are_friends


class RegisterView(generics.CreateAPIView):
	serializer_class = RegisterSerializer
	permission_classes = (permissions.AllowAny,)
	throttle_classes = (RegisterAnonThrottle,)

	def create(self, request, *args, **kwargs):
		serializer = self.get_serializer(data=request.data)
		serializer.is_valid(raise_exception=True)
		result = serializer.save()
		return Response(result, status=status.HTTP_201_CREATED)


class ProfileView(generics.RetrieveUpdateDestroyAPIView):
	serializer_class = ProfileSerializer

	def get_object(self):
		return self.request.user.profile

	def destroy(self, request, *args, **kwargs):
		"""Right to erasure. Anonymises rather than dropping the row — see
		accounts.services.account_deletion and docs/PRODUCT_DECISIONS.md D-009.
		"""
		serializer = AccountDeletionSerializer(data=request.data, context={"request": request})
		serializer.is_valid(raise_exception=True)
		anonymise_user(request.user)
		return Response(status=status.HTTP_204_NO_CONTENT)


class DietaryPreferenceListView(generics.ListAPIView):
	"""Read-only list of available dietary preferences. Rows are seeded by
	migration; not user-creatable. Frontend uses this to populate the
	multi-select on the profile edit screen."""

	serializer_class = DietaryPreferenceSerializer
	queryset = DietaryPreference.objects.all()
	pagination_class = None


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


class UserSearchView(generics.ListAPIView):
	serializer_class = UserPublicSerializer
	throttle_classes = (UserSearchThrottle,)

	def get_queryset(self):
		query = self.request.query_params.get("q", "").strip()
		# Require at least 3 chars to reduce mass enumeration by short prefixes.
		if not query or len(query) < 3:
			return User.objects.none()

		email_ids = User.objects.filter(email__iexact=query).values_list("id", flat=True)
		name_ids = User.objects.filter(profile__display_name__icontains=query).values_list(
			"id", flat=True
		)
		phone_ids = User.objects.filter(profile__phone__iexact=query).values_list("id", flat=True)
		matching_ids = set(email_ids) | set(name_ids) | set(phone_ids)
		matching_ids.discard(self.request.user.id)

		return User.objects.filter(id__in=matching_ids).select_related("profile")[:20]


class FriendshipViewSet(viewsets.ModelViewSet):
	serializer_class = FriendshipSerializer
	http_method_names = ["get", "post", "patch", "delete"]

	def get_queryset(self):
		user = self.request.user
		return Friendship.objects.filter(Q(from_user=user) | Q(to_user=user)).select_related(
			"from_user__profile", "to_user__profile"
		)

	def partial_update(self, request, *args, **kwargs):
		instance = self.get_object()
		# Only the recipient can accept/decline
		if instance.to_user != request.user:
			return Response(
				{"detail": "Only the recipient can respond to a friend request."},
				status=status.HTTP_403_FORBIDDEN,
			)
		new_status = request.data.get("status")
		if new_status not in (Friendship.Status.ACCEPTED, Friendship.Status.DECLINED):
			return Response(
				{"detail": "status must be 'accepted' or 'declined'."},
				status=status.HTTP_400_BAD_REQUEST,
			)
		instance.status = new_status
		instance.save(update_fields=["status", "updated_at"])
		return Response(self.get_serializer(instance).data)

	@action(detail=False, methods=["get"])
	def requests(self, request):
		"""Pending requests received by the current user."""
		qs = Friendship.objects.filter(
			to_user=request.user, status=Friendship.Status.PENDING
		).select_related("from_user__profile", "to_user__profile")
		serializer = self.get_serializer(qs, many=True)
		return Response(serializer.data)

	@action(detail=False, methods=["get"])
	def friends(self, request):
		"""Accepted friendships for the current user."""
		qs = Friendship.objects.filter(
			Q(from_user=request.user) | Q(to_user=request.user),
			status=Friendship.Status.ACCEPTED,
		).select_related("from_user__profile", "to_user__profile")
		serializer = self.get_serializer(qs, many=True)
		return Response(serializer.data)


class EmailInvitationView(generics.ListCreateAPIView):
	serializer_class = EmailInvitationSerializer
	pagination_class = None

	def get_throttles(self):
		# Apply the strict invite throttle only to POST so the inviter can
		# always reload the "pending invites" list without burning the quota.
		if self.request.method == "POST":
			return [InviteThrottle()]
		return []

	def get_queryset(self):
		# Only the user's own outgoing invitations, newest first. Used by the
		# friends "Pending" UI so the inviter can see whom they've already
		# invited via email.
		return EmailInvitation.objects.filter(from_user=self.request.user, accepted=False).order_by(
			"-created_at"
		)

	def perform_create(self, serializer):
		invitation = serializer.save()
		from_user = invitation.from_user
		sender_name = (
			getattr(from_user.profile, "display_name", "") or from_user.email.split("@")[0]
		)
		invite_url = getattr(settings, "APP_PUBLIC_URL", "https://lovemuse.app")
		language = self.request.data.get("language")
		# Decision (D-008): if Resend fails, the invitation row stays in DB
		# and the inviter still gets a 201. Failure is logged with context so
		# the admin can resend manually. Atomic rollback would lose the row
		# on transient Resend hiccups.
		try:
			send_invitation_email(
				to_email=invitation.email,
				inviter_name=sender_name,
				invitation_link=f"{invite_url}/",
				language=language,
			)
		except EmailSendError as exc:
			logger.warning(
				"Invitation email not sent (status=%s) for %s: %s",
				exc.status_code,
				invitation.email,
				exc.message,
			)


class PublicProfileView(generics.RetrieveAPIView):
	serializer_class = ProfileSerializer

	def get_object(self):
		user = get_object_or_404(
			User.objects.select_related("profile"),
			pk=self.kwargs["user_id"],
		)
		require_can_view(self.request.user, user)
		return user.profile


class UserPinsView(generics.ListAPIView):
	serializer_class = PinSerializer
	pagination_class = None

	def get_queryset(self):
		user = get_object_or_404(User, pk=self.kwargs["user_id"])
		require_can_view(self.request.user, user)
		# Through the shared selector so `?status=all` means the same thing
		# here as it does on /pins/ — it used to be passed through as a
		# literal status and returned nothing.
		return visible_pins(
			self.request.user,
			owner=user,
			status=self.request.query_params.get("status"),
		)


# El cuerpo es literalmente el mismo objeto para todos los caminos de
# PasswordResetView: exista la cuenta, no exista, o falle Resend (RF2). Si
# alguna vez hay que tocarlo, se toca acá y sigue siendo uno solo.
PASSWORD_RESET_ACCEPTED = {"detail": "If an account exists for that email, a code has been sent."}


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
		return Response({"detail": "Password updated."}, status=status.HTTP_200_OK)
