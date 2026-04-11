from rest_framework import serializers

from accounts.serializers import UserPublicSerializer
from feed.models import Activity
from pins.serializers import PinSerializer


class ActivitySerializer(serializers.ModelSerializer):
	actor = UserPublicSerializer(read_only=True)
	pin = PinSerializer(read_only=True)
	target_user = UserPublicSerializer(read_only=True)

	class Meta:
		model = Activity
		fields = ("id", "actor", "verb", "pin", "target_user", "created_at")
