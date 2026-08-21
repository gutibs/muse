from rest_framework import serializers

from pins.models import Pin, SharedList, SharedListItem
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
			"is_favourite",
			"created_at",
			"updated_at",
		)
		# `is_favourite` se lee acá pero se escribe por su propia acción: un
		# PATCH común tocaría `updated_at` (auto_now) y, con
		# `ordering = ["-updated_at"]`, la lista saltaría bajo el dedo.
		read_only_fields = ("id", "created_at", "updated_at", "is_favourite")

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
	# La selección viaja como una lista ordenada de pins: el orden del array
	# es el orden de la lista, y mandarla completa reemplaza la anterior. Es
	# más simple para el cliente que un endpoint de items con posiciones.
	pin_ids = serializers.ListField(
		child=serializers.IntegerField(),
		write_only=True,
		required=False,
	)
	items = serializers.SerializerMethodField()

	class Meta:
		model = SharedList
		fields = (
			"id",
			"token",
			"title",
			"kind",
			"status_filter",
			"is_active",
			"expires_at",
			"pin_ids",
			"items",
			"url",
			"created_at",
		)
		read_only_fields = ("id", "token", "url", "items", "created_at")

	def get_items(self, obj):
		return [
			{"pin": item.pin_id, "position": item.position, "note": item.note}
			for item in obj.items.all()
		]

	def validate_pin_ids(self, value):
		from pins.serializers_public import CURATED_ITEM_LIMIT

		if len(value) > CURATED_ITEM_LIMIT:
			raise serializers.ValidationError(
				f"A shortlist holds up to {CURATED_ITEM_LIMIT} places."
			)
		if len(set(value)) != len(value):
			raise serializers.ValidationError("The same place is in the list twice.")

		# Sólo pins propios: sin esto, cualquiera podría armar una lista
		# pública con las reseñas de otra persona.
		user = self.context["request"].user
		propios = set(Pin.objects.filter(user=user, id__in=value).values_list("id", flat=True))
		ajenos = [pid for pid in value if pid not in propios]
		if ajenos:
			raise serializers.ValidationError(f"Not your pins: {ajenos}")
		return value

	def _set_items(self, instance, pin_ids):
		instance.items.all().delete()
		SharedListItem.objects.bulk_create(
			[
				SharedListItem(shared_list=instance, pin_id=pid, position=posicion)
				for posicion, pid in enumerate(pin_ids)
			]
		)

	def get_url(self, obj):
		# Absolute URL so the link is shareable from the mobile app, where
		# window.location.origin is "http://localhost" (Capacitor scheme) and
		# would otherwise produce a useless link.
		from django.conf import settings

		base = getattr(settings, "APP_PUBLIC_URL", "https://lovemuse.app").rstrip("/")
		return f"{base}/shared/{obj.token}"

	def create(self, validated_data):
		pin_ids = validated_data.pop("pin_ids", None)
		validated_data["user"] = self.context["request"].user
		instance = super().create(validated_data)
		if pin_ids is not None:
			self._set_items(instance, pin_ids)
		return instance

	def update(self, instance, validated_data):
		pin_ids = validated_data.pop("pin_ids", None)
		instance = super().update(instance, validated_data)
		if pin_ids is not None:
			self._set_items(instance, pin_ids)
		return instance


# SharedListPublicSerializer used to live here and reuse PinSerializer, which
# leaked every internal restaurant field to anyone holding a share link. The
# anonymous payload now has its own module — see pins/serializers_public.py.
