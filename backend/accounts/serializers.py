from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.models import Profile

User = get_user_model()


class ProfileSerializer(serializers.ModelSerializer):
	email = serializers.EmailField(source="user.email", read_only=True)
	stats = serializers.SerializerMethodField()

	class Meta:
		model = Profile
		fields = (
			"id",
			"email",
			"display_name",
			"bio",
			"avatar",
			"city",
			"stats",
			"created_at",
		)
		read_only_fields = ("id", "email", "stats", "created_at")

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
		if User.objects.filter(email=value).exists():
			raise serializers.ValidationError("A user with this email already exists.")
		return value.lower()

	def create(self, validated_data):
		user = User.objects.create_user(
			username=validated_data["email"],
			email=validated_data["email"],
			password=validated_data["password"],
		)
		if validated_data.get("display_name"):
			user.profile.display_name = validated_data["display_name"]
			user.profile.save(update_fields=["display_name"])

		# Check for pending email invitations
		from accounts.models import EmailInvitation, Friendship

		invitations = EmailInvitation.objects.filter(
			email=validated_data["email"],
			accepted=False,
		)
		for invitation in invitations:
			Friendship.objects.create(
				from_user=invitation.from_user,
				to_user=user,
				status=Friendship.Status.PENDING,
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


class ChangePasswordSerializer(serializers.Serializer):
	current_password = serializers.CharField(write_only=True)
	new_password = serializers.CharField(write_only=True, validators=[validate_password])

	def validate_current_password(self, value):
		if not self.context["request"].user.check_password(value):
			raise serializers.ValidationError("Current password is incorrect.")
		return value
