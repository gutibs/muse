from rest_framework import serializers

from pins.models import Pin, SharedList
from restaurants.models import Tag
from restaurants.serializers import RestaurantSerializer


class PinTagSerializer(serializers.ModelSerializer):
	"""Las etiquetas de un pin, con su eje.

	`kind` viaja al cliente porque es lo que le permite agrupar en vibe,
	occasion y scene sin mantener su propia tabla de qué etiqueta va en qué
	grupo. `icon` y `color`, que traía el viejo modelo Persona, no existen en
	Tag y no los usaba nadie.
	"""

	class Meta:
		model = Tag
		fields = ("id", "name", "slug", "kind")


class PinSerializer(serializers.ModelSerializer):
	restaurant_detail = RestaurantSerializer(source="restaurant", read_only=True)
	tag_ids = serializers.PrimaryKeyRelatedField(
		queryset=Tag.objects.all(),
		many=True,
		source="tags",
		write_only=True,
		required=False,
	)
	tags_detail = PinTagSerializer(source="tags", many=True, read_only=True)

	class Meta:
		model = Pin
		fields = (
			"id",
			"restaurant",
			"restaurant_detail",
			"status",
			"rating",
			"comment",
			"visited_at",
			"tag_ids",
			"tags_detail",
			"created_at",
			"updated_at",
		)
		read_only_fields = ("id", "created_at", "updated_at")

	def validate(self, data):
		status = data.get("status", getattr(self.instance, "status", None))
		rating = data.get("rating", getattr(self.instance, "rating", None))

		if status == Pin.Status.VISITED and rating is None:
			raise serializers.ValidationError(
				{"rating": "Rating is required for visited restaurants."}
			)
		if status == Pin.Status.TO_VISIT and rating is not None:
			raise serializers.ValidationError(
				{"rating": "Cannot rate a restaurant you have not visited."}
			)
		return data

	def create(self, validated_data):
		tags = validated_data.pop("tags", [])
		validated_data["user"] = self.context["request"].user
		pin = Pin.objects.create(**validated_data)
		if tags:
			pin.tags.set(tags)
		return pin

	def update(self, instance, validated_data):
		tags = validated_data.pop("tags", None)
		for attr, value in validated_data.items():
			setattr(instance, attr, value)
		instance.save()
		if tags is not None:
			instance.tags.set(tags)
		return instance


class SharedListSerializer(serializers.ModelSerializer):
	url = serializers.SerializerMethodField()

	class Meta:
		model = SharedList
		fields = ("id", "token", "title", "status_filter", "is_active", "url", "created_at")
		read_only_fields = ("id", "token", "url", "created_at")

	def get_url(self, obj):
		# Absolute URL so the link is shareable from the mobile app, where
		# window.location.origin is "http://localhost" (Capacitor scheme) and
		# would otherwise produce a useless link.
		from django.conf import settings

		base = getattr(settings, "APP_PUBLIC_URL", "https://lovemuse.app").rstrip("/")
		return f"{base}/shared/{obj.token}"

	def create(self, validated_data):
		validated_data["user"] = self.context["request"].user
		return super().create(validated_data)


# SharedListPublicSerializer used to live here and reuse PinSerializer, which
# leaked every internal restaurant field to anyone holding a share link. The
# anonymous payload now has its own module — see pins/serializers_public.py.
