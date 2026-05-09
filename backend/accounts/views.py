import logging

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle, UserRateThrottle

from accounts.models import DietaryPreference, Friendship
from accounts.serializers import (
	ChangePasswordSerializer,
	DietaryPreferenceSerializer,
	EmailInvitationSerializer,
	FriendshipSerializer,
	ProfileSerializer,
	RegisterSerializer,
	UserPublicSerializer,
)
from pins.models import Pin
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


def _are_friends(user_a, user_b) -> bool:
	if user_a == user_b:
		return True
	return Friendship.objects.filter(
		(Q(from_user=user_a, to_user=user_b) | Q(from_user=user_b, to_user=user_a)),
		status=Friendship.Status.ACCEPTED,
	).exists()


class RegisterView(generics.CreateAPIView):
	serializer_class = RegisterSerializer
	permission_classes = (permissions.AllowAny,)
	throttle_classes = (RegisterAnonThrottle,)

	def create(self, request, *args, **kwargs):
		serializer = self.get_serializer(data=request.data)
		serializer.is_valid(raise_exception=True)
		result = serializer.save()
		return Response(result, status=status.HTTP_201_CREATED)


class ProfileView(generics.RetrieveUpdateAPIView):
	serializer_class = ProfileSerializer

	def get_object(self):
		return self.request.user.profile


class DietaryPreferenceListView(generics.ListAPIView):
	"""Read-only list of available dietary preferences. Rows are seeded by
	migration; not user-creatable. Frontend uses this to populate the
	multi-select on the profile edit screen."""

	serializer_class = DietaryPreferenceSerializer
	queryset = DietaryPreference.objects.all()
	pagination_class = None


class ChangePasswordView(generics.GenericAPIView):
	serializer_class = ChangePasswordSerializer

	def post(self, request):
		serializer = self.get_serializer(data=request.data)
		serializer.is_valid(raise_exception=True)
		request.user.set_password(serializer.validated_data["new_password"])
		request.user.save()
		return Response(status=status.HTTP_204_NO_CONTENT)


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


class EmailInvitationView(generics.CreateAPIView):
	serializer_class = EmailInvitationSerializer
	throttle_classes = (InviteThrottle,)

	def perform_create(self, serializer):
		invitation = serializer.save()
		from_user = invitation.from_user
		sender_name = (
			getattr(from_user.profile, "display_name", "") or from_user.email.split("@")[0]
		)
		invite_url = getattr(settings, "APP_PUBLIC_URL", "https://lovemuse.app")
		# Email body in English by default. Most testers are English-speaking and
		# the previous Spanish wording was confusing. Tagged with the sender's
		# language ("language" field in request) when present.
		lang = (self.request.data.get("language") or "en").lower()[:2]
		if lang == "es":
			subject = f"{sender_name} te invitó a Muse"
			message = (
				f"Hola,\n\n"
				f"{sender_name} te invitó a Muse, una app para descubrir y compartir "
				f"restaurantes con amigos.\n\n"
				f"Registrate acá: {invite_url}/register\n\n"
				f"Cuando te registres con este email, se creará la amistad automáticamente.\n\n"
				f"— El equipo de Muse"
			)
		elif lang == "it":
			subject = f"{sender_name} ti ha invitato su Muse"
			message = (
				f"Ciao,\n\n"
				f"{sender_name} ti ha invitato su Muse, un'app per scoprire e "
				f"condividere ristoranti con gli amici.\n\n"
				f"Registrati qui: {invite_url}/register\n\n"
				f"Quando ti registri con questa email, l'amicizia sarà creata "
				f"automaticamente.\n\n"
				f"— Il team di Muse"
			)
		else:
			subject = f"{sender_name} invited you to Muse"
			message = (
				f"Hi,\n\n"
				f"{sender_name} invited you to Muse, an app to discover and share "
				f"restaurants with friends.\n\n"
				f"Sign up here: {invite_url}/register\n\n"
				f"When you sign up with this email, the friendship will be created "
				f"automatically.\n\n"
				f"— The Muse team"
			)
		from_email = getattr(settings, "DEFAULT_FROM_EMAIL", None)
		try:
			send_mail(
				subject=subject,
				message=message,
				from_email=from_email,
				recipient_list=[invitation.email],
				fail_silently=False,
			)
		except Exception:
			logger.exception("Failed to send invitation email to %s", invitation.email)


class PublicProfileView(generics.RetrieveAPIView):
	serializer_class = ProfileSerializer

	def get_object(self):
		user = get_object_or_404(
			User.objects.select_related("profile"),
			pk=self.kwargs["user_id"],
		)
		if not _are_friends(self.request.user, user):
			raise PermissionDenied("You are not friends with this user.")
		return user.profile


class UserPinsView(generics.ListAPIView):
	serializer_class = PinSerializer
	pagination_class = None

	def get_queryset(self):
		user = get_object_or_404(User, pk=self.kwargs["user_id"])
		if not _are_friends(self.request.user, user):
			raise PermissionDenied("You are not friends with this user.")

		qs = (
			Pin.objects.filter(user=user)
			.select_related("restaurant")
			.prefetch_related("personas", "restaurant__cuisines")
		)
		status_param = self.request.query_params.get("status")
		if status_param:
			qs = qs.filter(status=status_param)
		return qs
