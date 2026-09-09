"""Cómo se ve una persona para otra, y el grafo que las une.

`UserAnonymousSafeSerializer` es el que sale por endpoints públicos: no lleva
email. Se probó que no lo lleve, porque la lista compartida es anónima.
"""

import logging

from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from accounts.models import (
	EmailInvitation,
	Friendship,
)
from accounts.services.visibility import blocked_user_ids

User = get_user_model()

logger = logging.getLogger(__name__)


class UserPublicSerializer(serializers.ModelSerializer):
	display_name = serializers.CharField(source="profile.display_name")
	avatar = serializers.ImageField(source="profile.avatar")
	city = serializers.CharField(source="profile.city")
	is_deleted = serializers.SerializerMethodField()
	# El badge se declara acá, en la base, y no en cada superficie: de esta
	# clase cuelgan las seis formas en que una persona ve a otra (reseñas,
	# link compartido, feed, amistades, bloqueos y búsqueda), y una marca que
	# aparece en unas sí y en otras no se lee como que la persona la perdió.
	is_verified_insider = serializers.BooleanField(
		source="profile.is_verified_insider", read_only=True
	)

	class Meta:
		model = User
		fields = (
			"id",
			"email",
			"display_name",
			"avatar",
			"city",
			"is_deleted",
			"is_verified_insider",
		)

	def get_is_deleted(self, obj) -> bool:
		return getattr(obj.profile, "deleted_at", None) is not None


class UserAnonymousSafeSerializer(UserPublicSerializer):
	"""Identity without the email, for surfaces reachable without logging in.

	`UserPublicSerializer` carries the email, which is fine between
	authenticated friends but not on a public share link — those URLs get
	forwarded through chat apps and end up with strangers.
	"""

	class Meta(UserPublicSerializer.Meta):
		fields = ("id", "display_name", "avatar", "city", "is_deleted", "is_verified_insider")


class FriendshipSerializer(serializers.ModelSerializer):
	"""RF5 se resuelve por el queryset del campo, no por un mensaje.

	Sacar a los bloqueados de `to_user_id.queryset` hace que DRF genere para
	ellos exactamente el mismo error que para un id que no existe —mismo texto,
	mismo `code`— porque para el serializer *no existen*. Un mensaje propio,
	por parecido que fuera, se distingue: la validación del primary key corre
	antes que `validate_to_user_id`, así que un id inexistente nunca llega a
	nuestro código y el error propio delataba el bloqueo. Y decirle a un
	acosador "te bloquearon" es el resultado que RF2 existe para evitar.
	"""

	# Sin email: la contraparte de una amistad —y sobre todo la de una solicitud
	# que todavía no aceptaste— es alguien cuyo email no tenés por qué recibir.
	from_user = UserAnonymousSafeSerializer(read_only=True)
	to_user = UserAnonymousSafeSerializer(read_only=True)
	to_user_id = serializers.PrimaryKeyRelatedField(
		queryset=User.objects.all(), source="to_user", write_only=True
	)

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		request = self.context.get("request")
		if request is not None and request.user.is_authenticated:
			self.fields["to_user_id"].queryset = User.objects.exclude(
				id__in=blocked_user_ids(request.user)
			)

	class Meta:
		model = Friendship
		fields = ("id", "from_user", "to_user", "to_user_id", "status", "created_at")
		read_only_fields = ("id", "from_user", "status", "created_at")

	def validate_to_user_id(self, value):
		"""OJO CON EL NOMBRE: DRF resuelve `validate_<campo>` por el nombre del
		campo declarado, que acá es `to_user_id` —el de escritura—, no por el
		de su `source`. Mientras este método se llamó `validate_to_user`, las
		tres validaciones de abajo no corrieron nunca: se podía mandar una
		solicitud a uno mismo, y la duplicada salía como 500 desde el
		`unique_together` en vez de 400.
		"""
		request = self.context["request"]
		if value == request.user:
			raise serializers.ValidationError(_("You cannot send a friend request to yourself."))
		if Friendship.objects.filter(from_user=request.user, to_user=value).exists():
			raise serializers.ValidationError(_("Friend request already sent."))
		if Friendship.objects.filter(from_user=value, to_user=request.user).exists():
			raise serializers.ValidationError(_("This user already sent you a friend request."))
		return value

	def create(self, validated_data):
		validated_data["from_user"] = self.context["request"].user
		validated_data["status"] = Friendship.Status.PENDING
		return super().create(validated_data)


class EmailInvitationSerializer(serializers.ModelSerializer):
	class Meta:
		model = EmailInvitation
		fields = ("id", "email", "accepted", "created_at")
		read_only_fields = ("id", "accepted", "created_at")

	def validate_email(self, value):
		value = value.lower()
		request = self.context["request"]

		existing = EmailInvitation.objects.filter(
			from_user=request.user, email__iexact=value
		).first()
		if existing and existing.accepted:
			raise serializers.ValidationError(_("This person already accepted your invitation."))
		return value

	def create(self, validated_data):
		request = self.context["request"]
		email = validated_data["email"]
		# Re-send support: if an unaccepted invitation already exists, reuse it
		# (touch updated_at) so the view can trigger a fresh email.
		from django.utils import timezone

		existing = EmailInvitation.objects.filter(
			from_user=request.user, email__iexact=email, accepted=False
		).first()
		if existing:
			existing.created_at = timezone.now()
			existing.save(update_fields=["created_at"])
			return existing
		validated_data["from_user"] = request.user
		return super().create(validated_data)
