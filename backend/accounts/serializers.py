from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.consent import POLICY_VERSIONS
from accounts.models import (
	Block,
	ConsentRecord,
	DietaryPreference,
	EmailInvitation,
	Friendship,
	Profile,
	Report,
)
from accounts.services.blocking import is_blocked
from accounts.services.visibility import blocked_user_ids
from pins.models import Pin

User = get_user_model()


class DietaryPreferenceSerializer(serializers.ModelSerializer):
	class Meta:
		model = DietaryPreference
		fields = ("id", "name", "slug")


class ProfileSerializer(serializers.ModelSerializer):
	email = serializers.EmailField(source="user.email", read_only=True)
	stats = serializers.SerializerMethodField()
	favourite_cuisine_detail = serializers.SerializerMethodField()
	dietary_preferences = serializers.PrimaryKeyRelatedField(
		queryset=DietaryPreference.objects.all(),
		many=True,
		required=False,
	)
	dietary_preferences_detail = DietaryPreferenceSerializer(
		source="dietary_preferences", many=True, read_only=True
	)

	class Meta:
		model = Profile
		fields = (
			"id",
			"email",
			"display_name",
			"bio",
			"avatar",
			"city",
			"website",
			"instagram",
			"phone",
			"favourite_cuisine",
			"favourite_cuisine_detail",
			"dietary_preferences",
			"dietary_preferences_detail",
			"analytics_opt_out",
			"stats",
			"created_at",
		)
		read_only_fields = (
			"id",
			"email",
			"stats",
			"favourite_cuisine_detail",
			"dietary_preferences_detail",
			"created_at",
		)

	def get_favourite_cuisine_detail(self, obj):
		if obj.favourite_cuisine:
			return {
				"id": obj.favourite_cuisine.id,
				"name": obj.favourite_cuisine.name,
				"slug": obj.favourite_cuisine.slug,
			}
		return None

	def get_stats(self, obj):
		user = obj.user
		return {
			"pin_count": user.pins.count(),
			"visited_count": user.pins.filter(status="visited").count(),
			"to_visit_count": user.pins.filter(status="to_visit").count(),
			"friend_count": (
				user.friendships_sent.filter(status="accepted").count()
				+ user.friendships_received.filter(status="accepted").count()
			),
		}


class RegisterSerializer(serializers.Serializer):
	email = serializers.EmailField()
	password = serializers.CharField(write_only=True, validators=[validate_password])
	display_name = serializers.CharField(max_length=100, required=False, default="")
	# Active consent: a single unified privacy checkbox, required and must be
	# explicitly True. A missing or False value is a 400 — the client cannot
	# register without ticking it. Accepting the unified policy still persists
	# one ConsentRecord per framework (GDPR + PDPO) as legal proof.
	accept_privacy = serializers.BooleanField(write_only=True)

	def validate_email(self, value):
		value = value.lower()
		if User.objects.filter(email__iexact=value).exists():
			raise serializers.ValidationError("A user with this email already exists.")
		return value

	def validate_accept_privacy(self, value):
		if value is not True:
			raise serializers.ValidationError("You must accept the privacy policy to register.")
		return value

	def _client_ip(self):
		request = self.context.get("request")
		if request is None:
			return None
		forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
		if forwarded:
			return forwarded.split(",")[0].strip()
		return request.META.get("REMOTE_ADDR")

	def _consume_invitations(self, user):
		"""Convierte en amistad las invitaciones dirigidas al email de `user`.

		ACCEPTED y no PENDING: el mail de invitación promete que la amistad se
		crea sola, y registrarse por ahí es el consentimiento. Ver D-005.
		"""
		invitations = EmailInvitation.objects.filter(
			email__iexact=user.email,
			accepted=False,
		)
		for invitation in invitations:
			# La amistad se crea sin acto de quien se registra, así que un
			# bloqueo se revertiría solo por este camino. Hoy no hay forma de
			# llegar acá —para tener un bloqueo hace falta una cuenta, y con
			# cuenta no te registrás—, pero el invariante "un bloqueo no se
			# revierte solo" se rompe en silencio, y alcanza con que exista un
			# "cambiar mi email" para volverlo alcanzable.
			if is_blocked(invitation.from_user, user):
				continue
			Friendship.objects.create(
				from_user=invitation.from_user,
				to_user=user,
				status=Friendship.Status.ACCEPTED,
			)
			invitation.accepted = True
			invitation.save(update_fields=["accepted"])

	def create(self, validated_data):
		user = User.objects.create_user(
			username=validated_data["email"],
			email=validated_data["email"],
			password=validated_data["password"],
		)
		if validated_data.get("display_name"):
			user.profile.display_name = validated_data["display_name"]
			user.profile.save(update_fields=["display_name"])

		ip = self._client_ip()
		ConsentRecord.objects.bulk_create(
			[
				ConsentRecord(
					user=user,
					policy=policy,
					policy_version=POLICY_VERSIONS[policy],
					ip_address=ip,
				)
				for policy in (ConsentRecord.Policy.GDPR, ConsentRecord.Policy.PDPO)
			]
		)

		self._consume_invitations(user)

		refresh = RefreshToken.for_user(user)
		return {
			"user": ProfileSerializer(user.profile).data,
			"tokens": {
				"access": str(refresh.access_token),
				"refresh": str(refresh),
			},
		}


class UserPublicSerializer(serializers.ModelSerializer):
	display_name = serializers.CharField(source="profile.display_name")
	avatar = serializers.ImageField(source="profile.avatar")
	city = serializers.CharField(source="profile.city")
	is_deleted = serializers.SerializerMethodField()

	class Meta:
		model = User
		fields = ("id", "email", "display_name", "avatar", "city", "is_deleted")

	def get_is_deleted(self, obj) -> bool:
		return getattr(obj.profile, "deleted_at", None) is not None


class UserAnonymousSafeSerializer(UserPublicSerializer):
	"""Identity without the email, for surfaces reachable without logging in.

	`UserPublicSerializer` carries the email, which is fine between
	authenticated friends but not on a public share link — those URLs get
	forwarded through chat apps and end up with strangers.
	"""

	class Meta(UserPublicSerializer.Meta):
		fields = ("id", "display_name", "avatar", "city", "is_deleted")


class AccountDeletionSerializer(serializers.Serializer):
	"""Erasure is irreversible, so an access token is not enough on its own —
	the caller re-proves the password. Protects against a device left unlocked
	or a leaked token nuking someone's account."""

	current_password = serializers.CharField(write_only=True)

	def validate_current_password(self, value):
		if not self.context["request"].user.check_password(value):
			raise serializers.ValidationError("Current password is incorrect.")
		return value


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

	from_user = UserPublicSerializer(read_only=True)
	to_user = UserPublicSerializer(read_only=True)
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
			raise serializers.ValidationError("You cannot send a friend request to yourself.")
		if Friendship.objects.filter(from_user=request.user, to_user=value).exists():
			raise serializers.ValidationError("Friend request already sent.")
		if Friendship.objects.filter(from_user=value, to_user=request.user).exists():
			raise serializers.ValidationError("This user already sent you a friend request.")
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
		if User.objects.filter(email__iexact=value).exists():
			raise serializers.ValidationError(
				"This user is already on Muse. Search for them by email instead."
			)
		existing = EmailInvitation.objects.filter(
			from_user=request.user, email__iexact=value
		).first()
		if existing and existing.accepted:
			raise serializers.ValidationError("This person already accepted your invitation.")
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


class ChangePasswordSerializer(serializers.Serializer):
	current_password = serializers.CharField(write_only=True)
	new_password = serializers.CharField(write_only=True, validators=[validate_password])

	def validate_current_password(self, value):
		if not self.context["request"].user.check_password(value):
			raise serializers.ValidationError("Current password is incorrect.")
		return value


class PasswordResetRequestSerializer(serializers.Serializer):
	"""Sólo valida la forma del email. Que exista o no la cuenta no se
	responde acá ni en ningún lado (RF2)."""

	email = serializers.EmailField()
	language = serializers.CharField(required=False, allow_blank=True)


class PasswordResetConfirmSerializer(serializers.Serializer):
	"""La validación del código y de la contraseña vive en
	accounts.services.password_reset.confirm_reset — un solo lugar, como pide
	el CLAUDE.md. Acá sólo la forma."""

	email = serializers.EmailField()
	code = serializers.CharField(max_length=12)
	new_password = serializers.CharField(write_only=True)
	# Sólo para traducir los errores de validación de la contraseña: la API no
	# tiene LocaleMiddleware, así que sin esto salen siempre en español.
	language = serializers.CharField(required=False, allow_blank=True)


class BlockSerializer(serializers.ModelSerializer):
	"""Un bloqueo, tal como lo ve quien lo hizo.

	Devuelve `user` (el bloqueado) y no `blocker`: este serializer sólo se usa
	para la lista propia, y quien la pide ya sabe que es él. Nunca se serializa
	un bloqueo recibido — eso le diría al bloqueado que lo bloquearon (RF2).
	"""

	# Sin email: se puede bloquear a CUALQUIERA por id, sin relación previa, así
	# que con UserPublicSerializer alcanzaba con recorrer ids —bloquear, leer,
	# desbloquear— para cosechar las direcciones de toda la base. Es la misma
	# fuga que se arregló en el feed; nada de la app usa este campo.
	user = UserAnonymousSafeSerializer(source="blocked", read_only=True)

	class Meta:
		model = Block
		fields = ("id", "user", "created_at")
		read_only_fields = fields


class ReportSerializer(serializers.ModelSerializer):
	"""Alta de una denuncia. Sólo escritura: nadie lista denuncias desde la app
	—ni el que reporta ni el reportado—, se resuelven en el admin."""

	reported_user_id = serializers.PrimaryKeyRelatedField(
		queryset=User.objects.all(), source="reported_user", write_only=True
	)
	pin_id = serializers.PrimaryKeyRelatedField(
		queryset=Pin.objects.all(), source="pin", write_only=True, required=False, allow_null=True
	)

	class Meta:
		model = Report
		fields = ("id", "reported_user_id", "pin_id", "reason", "detail", "created_at")
		read_only_fields = ("id", "created_at")


class BlockCreateSerializer(serializers.Serializer):
	"""Sólo valida la entrada de `POST /auth/blocks/`.

	Existe para que un `userId` ausente o no numérico dé 400 y no un 500: el
	`get_object_or_404` que había atrapa `DoesNotExist`, no el `ValueError` que
	tira el ORM cuando la pk no es un número.
	"""

	user_id = serializers.PrimaryKeyRelatedField(queryset=User.objects.all())
