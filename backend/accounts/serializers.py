from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.models import EmailInvitation, Friendship, Profile

User = get_user_model()


class ProfileSerializer(serializers.ModelSerializer):
	email = serializers.EmailField(source="user.email", read_only=True)
	stats = serializers.SerializerMethodField()
	favourite_cuisine_detail = serializers.SerializerMethodField()

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
			"dietary",
			"stats",
			"created_at",
		)
		read_only_fields = ("id", "email", "stats", "favourite_cuisine_detail", "created_at")

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

	def validate_email(self, value):
		value = value.lower()
		if User.objects.filter(email__iexact=value).exists():
			raise serializers.ValidationError("A user with this email already exists.")
		return value

	def create(self, validated_data):
		user = User.objects.create_user(
			username=validated_data["email"],
			email=validated_data["email"],
			password=validated_data["password"],
		)
		if validated_data.get("display_name"):
			user.profile.display_name = validated_data["display_name"]
			user.profile.save(update_fields=["display_name"])

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

	class Meta:
		model = User
		fields = ("id", "email", "display_name", "avatar", "city")


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

	def validate_to_user(self, value):
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
