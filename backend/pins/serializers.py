from rest_framework import serializers

from pins.models import Persona, Pin
from restaurants.serializers import RestaurantSerializer


class PersonaSerializer(serializers.ModelSerializer):
	class Meta:
		model = Persona
		fields = ("id", "name", "slug", "icon", "color")


class PinSerializer(serializers.ModelSerializer):
	restaurant_detail = RestaurantSerializer(source="restaurant", read_only=True)
	persona_ids = serializers.PrimaryKeyRelatedField(
		queryset=Persona.objects.all(),
		many=True,
		source="personas",
		write_only=True,
		required=False,
	)
	personas_detail = PersonaSerializer(source="personas", many=True, read_only=True)

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
			"persona_ids",
			"personas_detail",
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
		personas = validated_data.pop("personas", [])
		validated_data["user"] = self.context["request"].user
		pin = Pin.objects.create(**validated_data)
		if personas:
			pin.personas.set(personas)
		return pin

	def update(self, instance, validated_data):
		personas = validated_data.pop("personas", None)
		for attr, value in validated_data.items():
			setattr(instance, attr, value)
		instance.save()
		if personas is not None:
			instance.personas.set(personas)
		return instance
