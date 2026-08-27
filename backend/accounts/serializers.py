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
)
from accounts.services.blocking import is_blocked

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

		invitations = EmailInvitation.objects.filter(
			email__iexact=validated_data["email"],
			accepted=False,
		)
		for invitation in invitations:
			# ACCEPTED, not PENDING. The invite email promises the friendship
			# is created automatically — registering via the invite link is
			# the user's consent. See docs/PRODUCT_DECISIONS.md D-005.
			Friendship.objects.create(
				from_user=invitation.from_user,
				to_user=user,
				status=Friendship.Status.ACCEPTED,
			)
			invitation.accepted = True
			invitation.save(update_fields=["accepted"])

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
	from_user = UserPublicSerializer(read_only=True)
	to_user = UserPublicSerializer(read_only=True)
	to_user_id = serializers.PrimaryKeyRelatedField(
		queryset=User.objects.all(), source="to_user", write_only=True
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
		# RF5: hay bloqueo en alguna dirección. El mensaje es deliberadamente
		# el mismo que el de un destinatario inexistente: decir "te bloquearon"
		# convertiría este endpoint en el oráculo que RF2 existe para cerrar.
		if is_blocked(request.user, value):
			raise serializers.ValidationError("This user is not available.")
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

	user = UserPublicSerializer(source="blocked", read_only=True)

	class Meta:
		model = Block
		fields = ("id", "user", "created_at")
		read_only_fields = fields
