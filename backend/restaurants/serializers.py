from django.contrib.gis.geos import Point
from rest_framework import serializers

from restaurants.models import Cuisine, Restaurant, Tag


class CuisineSerializer(serializers.ModelSerializer):
	class Meta:
		model = Cuisine
		fields = ("id", "name", "slug")


class TagSerializer(serializers.ModelSerializer):
	class Meta:
		model = Tag
		fields = ("id", "name", "slug")


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
			"created_at",
		)
		read_only_fields = ("id", "created_at")

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
