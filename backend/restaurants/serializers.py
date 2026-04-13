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
		fields = ("id", "name", "slug")


class MenuItemSerializer(serializers.ModelSerializer):
	class Meta:
		model = MenuItem
		fields = (
			"id", "name", "description", "price", "currency",
			"category", "is_recommended", "is_vegetarian", "is_gluten_free",
			"image_url",
		)


class RestaurantSerializer(serializers.ModelSerializer):
	latitude = serializers.FloatField(write_only=True, required=False)
	longitude = serializers.FloatField(write_only=True, required=False)
	lat = serializers.SerializerMethodField()
	lng = serializers.SerializerMethodField()
	cuisine_detail = CuisineSerializer(source="cuisine", read_only=True)
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
			"cuisine",
			"cuisine_detail",
			"tag_ids",
			"tags_detail",
			"price_level",
			"quality_level",
			"website",
			"phone",
			"average_rating",
			"pin_count",
			"approval_status",
			"created_at",
		)
		read_only_fields = ("id", "approval_status", "created_at")

	def get_lat(self, obj):
		return obj.location.y if obj.location else None

	def get_lng(self, obj):
		return obj.location.x if obj.location else None

	def validate(self, data):
		lat = data.pop("latitude", None)
		lng = data.pop("longitude", None)
		if lat is not None and lng is not None:
			data["location"] = Point(lng, lat, srid=4326)
		elif not self.instance:
			raise serializers.ValidationError("latitude and longitude are required.")
		return data

	def create(self, validated_data):
		tags = validated_data.pop("tags", [])
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
		return restaurant

	def update(self, instance, validated_data):
		tags = validated_data.pop("tags", None)
		for attr, value in validated_data.items():
			setattr(instance, attr, value)
		instance.save()
		if tags is not None:
			instance.tags.set(tags)
		return instance


class RestaurantDetailSerializer(RestaurantSerializer):
	menu_items = MenuItemSerializer(many=True, read_only=True)
	reviews = serializers.SerializerMethodField()

	class Meta(RestaurantSerializer.Meta):
		fields = RestaurantSerializer.Meta.fields + ("menu_items", "reviews")

	def get_reviews(self, obj):
		from pins.models import Pin
		pins = (
			Pin.objects.filter(restaurant=obj, status="visited", comment__gt="")
			.select_related("user__profile")
			.order_by("-updated_at")[:20]
		)
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
			}
			for p in pins
		]
