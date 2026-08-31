from django.contrib.gis.geos import Point
from rest_framework import serializers

from accounts.serializers import UserAnonymousSafeSerializer
from accounts.services.visibility import (
	blocked_user_ids,
	visible_friend_ids,
	visible_pin_filter,
)
from places.services.place_photos import attributions_for_place
from restaurants.models import Cuisine, MenuItem, Restaurant, Tag


class CuisineSerializer(serializers.ModelSerializer):
	class Meta:
		model = Cuisine
		fields = ("id", "name", "slug")


class TagSerializer(serializers.ModelSerializer):
	class Meta:
		model = Tag
		fields = ("id", "name", "slug", "kind")


class MenuItemSerializer(serializers.ModelSerializer):
	tags = TagSerializer(many=True, read_only=True)
	tag_ids = serializers.PrimaryKeyRelatedField(
		queryset=Tag.objects.all(),
		many=True,
		write_only=True,
		required=False,
		source="tags",
	)

	class Meta:
		model = MenuItem
		fields = (
			"id",
			"name",
			"description",
			"price",
			"currency",
			"category",
			"tags",
			"tag_ids",
			"image_url",
		)


class RestaurantSerializer(serializers.ModelSerializer):
	latitude = serializers.FloatField(write_only=True, required=False)
	longitude = serializers.FloatField(write_only=True, required=False)
	lat = serializers.SerializerMethodField()
	lng = serializers.SerializerMethodField()
	# Se escribe cruda y se lee clasificada: `reservation` es None mientras la
	# URL esté pendiente de revisión.
	reservation_url = serializers.URLField(
		write_only=True, required=False, allow_blank=True, max_length=500
	)
	reservation = serializers.SerializerMethodField()
	cuisines = serializers.PrimaryKeyRelatedField(
		queryset=Cuisine.objects.all(),
		many=True,
		required=False,
	)
	cuisines_detail = CuisineSerializer(source="cuisines", many=True, read_only=True)
	tag_ids = serializers.PrimaryKeyRelatedField(
		queryset=Tag.objects.all(),
		many=True,
		source="tags",
		write_only=True,
		required=False,
	)
	tags_detail = TagSerializer(source="tags", many=True, read_only=True)
	average_rating = serializers.FloatField(read_only=True, default=None)
	pin_count = serializers.IntegerField(read_only=True, default=0)

	class Meta:
		model = Restaurant
		fields = (
			"id",
			"name",
			"lat",
			"lng",
			"latitude",
			"longitude",
			"address",
			"city",
			"district",
			"country",
			"image_url",
			"cuisines",
			"cuisines_detail",
			"tag_ids",
			"tags_detail",
			"price_level",
			"quality_level",
			"website",
			"reservation_url",
			"reservation",
			"phone",
			"average_rating",
			"pin_count",
			"approval_status",
			"is_closed",
			"google_place_id",
			"opening_hours",
			"created_at",
		)
		read_only_fields = (
			"id",
			"approval_status",
			# Dato del catálogo, no del creador: lo pone Google o el admin.
			"is_closed",
			"is_closed",
			"created_at",
			"google_place_id",
			"average_rating",
			"pin_count",
			# Writable until now, which meant the same column could hold either
			# our own photo proxy URL or anything a client felt like sending.
			# It is only ever set from a parsed Google payload.
			"image_url",
		)

	def get_reservation(self, obj):
		"""La URL de reserva sólo sale de acá cuando pasó la clasificación.

		Es un dato que escribe un usuario y que se le muestra a todos los
		demás como "reservá": mientras esté pendiente de revisión, para la
		API no existe.
		"""
		if obj.reservation_status != Restaurant.ReservationStatus.APPROVED:
			return None
		if not obj.reservation_url:
			return None
		return {"url": obj.reservation_url, "provider": obj.reservation_provider}

	def get_lat(self, obj):
		return obj.location.y if obj.location else None

	def get_lng(self, obj):
		return obj.location.x if obj.location else None

	def validate(self, data):
		lat = data.pop("latitude", None)
		lng = data.pop("longitude", None)
		if lat is not None and lng is not None:
			data["location"] = Point(lng, lat, srid=4326)
		elif lat is not None or lng is not None:
			raise serializers.ValidationError("latitude and longitude must be provided together.")
		elif not self.instance:
			raise serializers.ValidationError("latitude and longitude are required.")
		return data

	def create(self, validated_data):
		tags = validated_data.pop("tags", [])
		cuisines = validated_data.pop("cuisines", [])
		validated_data["created_by"] = self.context["request"].user
		# Force pending unless admin
		user = self.context["request"].user
		if not (user.is_staff or user.is_superuser):
			validated_data["approval_status"] = Restaurant.ApprovalStatus.PENDING
		else:
			validated_data.setdefault("approval_status", Restaurant.ApprovalStatus.APPROVED)
		restaurant = Restaurant.objects.create(**validated_data)
		if tags:
			restaurant.tags.set(tags)
		if cuisines:
			restaurant.cuisines.set(cuisines)
		return restaurant

	def update(self, instance, validated_data):
		tags = validated_data.pop("tags", None)
		cuisines = validated_data.pop("cuisines", None)
		for attr, value in validated_data.items():
			setattr(instance, attr, value)
		instance.save()
		if tags is not None:
			instance.tags.set(tags)
		if cuisines is not None:
			instance.cuisines.set(cuisines)
		return instance


class RestaurantDetailSerializer(RestaurantSerializer):
	menu_items = MenuItemSerializer(many=True, read_only=True)
	reviews = serializers.SerializerMethodField()
	friend_stats = serializers.SerializerMethodField()
	photo_attribution = serializers.SerializerMethodField()

	class Meta(RestaurantSerializer.Meta):
		fields = RestaurantSerializer.Meta.fields + (
			"menu_items",
			"reviews",
			"friend_stats",
			"photo_attribution",
		)

	def get_photo_attribution(self, obj):
		"""Autor de la foto, exigido por los términos de Google.

		Se resuelve por `google_place_id` desde el details ya cacheado, en vez
		de guardar una segunda copia del dato en esta tabla. Sólo va en el
		detalle: en el listado sería un lookup por fila, y la decisión fue
		mostrar el crédito con la foto grande.
		"""
		if not obj.google_place_id or not obj.image_url:
			return []
		return attributions_for_place(obj.google_place_id)

	def _friend_ids(self):
		"""Cached per serializer instance: get_reviews and get_friend_stats
		both need it and would otherwise each hit the database."""
		if not hasattr(self, "_cached_friend_ids"):
			self._cached_friend_ids = visible_friend_ids(self.context["request"].user)
		return self._cached_friend_ids

	def _blocked_ids(self):
		"""Cacheado por instancia, igual que `_friend_ids`: el serializer se
		crea uno por request, así que esto es una query y no una por campo."""
		if not hasattr(self, "_cached_blocked_ids"):
			self._cached_blocked_ids = blocked_user_ids(self.context["request"].user)
		return self._cached_blocked_ids

	def get_friend_stats(self, obj):
		from django.db.models import Avg

		from pins.models import Pin

		friend_ids = self._friend_ids()
		if not friend_ids:
			return {"rating_avg": None, "rated_count": 0, "on_list_count": 0}

		# El filtro de visibilidad además del `user_id__in`: el promedio de
		# amigos se calcula sobre pocos datos y con un solo amigo pineado *es*
		# el rating de esa persona, así que un pin que su dueño restringió no
		# entra acá aunque el promedio global sí lo cuente (decisión 2.bis).
		friend_pins = Pin.objects.filter(restaurant=obj, user_id__in=friend_ids).filter(
			visible_pin_filter(self.context["request"].user)
		)
		rated = friend_pins.filter(status="visited", rating__isnull=False)
		on_list = friend_pins.filter(status="to_visit")

		avg = rated.aggregate(avg=Avg("rating"))["avg"]
		return {
			"rating_avg": round(avg, 1) if avg is not None else None,
			"rated_count": rated.count(),
			"on_list_count": on_list.count(),
		}

	def get_reviews(self, obj):
		from pins.models import Pin

		friend_ids = self._friend_ids()
		# D-001 no se deroga, se acota (F2.A): para cualquier tercero sin
		# bloqueo, las reseñas de los pins **públicos** —el default— siguen
		# visibles. Las que su autor restringió, no.
		pins = list(
			Pin.objects.filter(restaurant=obj, status="visited", comment__gt="")
			# El nivel y el bloqueo se aplican ACÁ, antes del corte. Filtrar la
			# lista ya cortada haría que quien bloqueó a alguien prolífico viera
			# un puñado de reseñas en un restaurante que tiene decenas.
			.filter(visible_pin_filter(self.context["request"].user))
			.select_related("user__profile")
			.order_by("-updated_at")[:20]
		)
		# Amistad primero, badge después: quién te conoce pesa más que quién
		# está verificado, y ese orden ya era una decisión tomada. El Insider
		# ordena *dentro* de cada grupo. El corte de 20 queda antes, sobre las
		# más recientes: esto cambia qué se lee primero, no qué reseñas hay.
		pins.sort(
			key=lambda p: (
				0 if p.user_id in friend_ids else 1,
				0 if p.user.profile.is_verified_insider else 1,
				-p.updated_at.timestamp(),
			)
		)
		# UserAnonymousSafeSerializer, not a hand-rolled dict: same author shape
		# as every other endpoint, no email (reviews are public to non-friends
		# by design, D-001), `is_deleted` for the anonymous byline, and an
		# absolute avatar URL — the dict emitted a MEDIA_URL-relative path that
		# could not resolve from the Capacitor WebView.
		return [
			{
				"id": p.id,
				"user": UserAnonymousSafeSerializer(p.user, context=self.context).data,
				"rating": p.rating,
				"comment": p.comment,
				"visited_at": p.visited_at,
				"created_at": p.created_at,
				"is_friend": p.user_id in friend_ids,
			}
			for p in pins
		]
