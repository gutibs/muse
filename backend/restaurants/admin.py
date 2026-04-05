from django.contrib.gis import admin as gis_admin

from restaurants.models import Cuisine, Restaurant, Tag


@gis_admin.register(Restaurant)
class RestaurantAdmin(gis_admin.GISModelAdmin):
	list_display = ("name", "city", "country", "cuisine", "price_level", "quality_level", "created_at")
	search_fields = ("name", "city", "country", "address")
	list_filter = ("cuisine", "price_level", "quality_level", "tags", "city")
	readonly_fields = ("created_at", "updated_at")
	filter_horizontal = ("tags",)


@gis_admin.register(Cuisine)
class CuisineAdmin(gis_admin.ModelAdmin):
	list_display = ("name", "slug")
	prepopulated_fields = {"slug": ("name",)}


@gis_admin.register(Tag)
class TagAdmin(gis_admin.ModelAdmin):
	list_display = ("name", "slug")
	prepopulated_fields = {"slug": ("name",)}
