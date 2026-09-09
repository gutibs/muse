"""Buscar gente, el grafo de amistades y las invitaciones por email."""

import logging

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.utils.translation import gettext_lazy as _
from rest_framework import generics, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from accounts.models import EmailInvitation, Friendship
from accounts.serializers import (
	EmailInvitationSerializer,
	FriendshipSerializer,
	UserAnonymousSafeSerializer,
)
from accounts.services.blocking import is_blocked
from accounts.services.email import EmailSendError, send_invitation_email
from accounts.services.friendships import are_friends
from accounts.services.visibility import blocked_user_ids
from accounts.views.throttles import InviteThrottle, UserSearchThrottle

logger = logging.getLogger(__name__)

User = get_user_model()


# Kept as a module-level alias for the tests that still import it from here.
# The implementation lives in accounts.services.friendships, next to
# friend_ids(); the views themselves now go through
# accounts.services.visibility, which answers the policy question rather than
# the question of fact.
_are_friends = are_friends


class UserSearchView(generics.ListAPIView):
	"""Encontrar a alguien de quien ya tenés el dato exacto.

	No es un directorio: no se busca por coincidencia parcial de nombre. Con
	`display_name__icontains` y tres caracteres, escribir "ana" devolvía a
	todas las Ana, Mariana y Susana de la plataforma —con su email— y eso es
	una lista de gente a la que mandarle solicitudes. Para encontrar a una
	persona hay que saber su email o su teléfono; si no, se la invita por mail.
	"""

	serializer_class = UserAnonymousSafeSerializer
	throttle_classes = (UserSearchThrottle,)

	def get_queryset(self):
		query = self.request.query_params.get("q", "").strip()
		if not query or len(query) < 3:
			return User.objects.none()

		email_ids = User.objects.filter(email__iexact=query).values_list("id", flat=True)
		phone_ids = User.objects.filter(profile__phone__iexact=query).values_list("id", flat=True)
		matching_ids = set(email_ids) | set(phone_ids)
		matching_ids.discard(self.request.user.id)
		# RF10. Esta vista no pasa por ningún service —es la que el plan daba
		# por perdida— así que el filtro va explícito. En las dos direcciones:
		# el conjunto de `blocked_user_ids` ya las junta.
		matching_ids -= blocked_user_ids(self.request.user)

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
				{"detail": _("Only the recipient can respond to a friend request.")},
				status=status.HTTP_403_FORBIDDEN,
			)
		new_status = request.data.get("status")
		if new_status not in (Friendship.Status.ACCEPTED, Friendship.Status.DECLINED):
			return Response(
				{"detail": _("status must be 'accepted' or 'declined'.")},
				status=status.HTTP_400_BAD_REQUEST,
			)
		# RF6: el bloqueo se comprueba acá y no sólo al crear la solicitud. Es
		# una carrera real: el otro bloquea mientras esta pantalla está abierta,
		# y sin este chequeo el PATCH crearía una amistad ACCEPTED posterior al
		# bloqueo — un bloqueo con una amistad viva debajo.
		if new_status == Friendship.Status.ACCEPTED and is_blocked(
			instance.from_user, instance.to_user
		):
			return Response(
				{"detail": _("This friend request is no longer available.")},
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
