from django.contrib.gis.geos import Point
from rest_framework import serializers

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
			"country",
			"image_url",
			"cuisines",
			"cuisines_detail",
			"tag_ids",
			"tags_detail",
			"price_level",
			"quality_level",
			"website",
			"phone",
			"average_rating",
			"pin_count",
			"approval_status",
			"google_place_id",
			"opening_hours",
			"created_at",
		)
		read_only_fields = (
			"id",
			"approval_status",
			"created_at",
			"google_place_id",
			"average_rating",
			"pin_count",
		)

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

	class Meta(RestaurantSerializer.Meta):
		fields = RestaurantSerializer.Meta.fields + ("menu_items", "reviews", "friend_stats")

	def _friend_ids(self):
		if hasattr(self, "_cached_friend_ids"):
			return self._cached_friend_ids
		from django.db.models import Q

		from accounts.models import Friendship

		user = self.context["request"].user
		if not user.is_authenticated:
			self._cached_friend_ids = set()
			return self._cached_friend_ids
		friendships = Friendship.objects.filter(
			Q(from_user=user) | Q(to_user=user),
			status=Friendship.Status.ACCEPTED,
		).values_list("from_user_id", "to_user_id")
		ids = set()
		for a, b in friendships:
			ids.add(a)
			ids.add(b)
		ids.discard(user.id)
		self._cached_friend_ids = ids
		return ids

	def get_friend_stats(self, obj):
		from django.db.models import Avg

		from pins.models import Pin

		friend_ids = self._friend_ids()
		if not friend_ids:
			return {"rating_avg": None, "rated_count": 0, "on_list_count": 0}

		friend_pins = Pin.objects.filter(restaurant=obj, user_id__in=friend_ids)
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
		pins = list(
			Pin.objects.filter(restaurant=obj, status="visited", comment__gt="")
			.select_related("user__profile")
			.order_by("-updated_at")[:20]
		)
		pins.sort(key=lambda p: (0 if p.user_id in friend_ids else 1, -p.updated_at.timestamp()))
		return [
			{
				"id": p.id,
				"user": {
					"id": p.user.id,
					"display_name": getattr(p.user.profile, "display_name", ""),
					"avatar": p.user.profile.avatar.url if p.user.profile.avatar else None,
				},
				"rating": p.rating,
				"comment": p.comment,
				"visited_at": p.visited_at,
				"created_at": p.created_at,
				"is_friend": p.user_id in friend_ids,
			}
			for p in pins
		]
