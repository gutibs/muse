from django.contrib import admin
from django.contrib.gis import admin as gis_admin

from restaurants.models import Cuisine, MenuItem, Restaurant, Tag


@admin.register(Restaurant)
class RestaurantAdmin(gis_admin.GISModelAdmin):
	list_display = ("name", "city", "country", "cuisine", "approval_status", "created_by", "created_at")
	search_fields = ("name", "city", "country", "address")
	list_filter = ("approval_status", "cuisine", "price_level", "quality_level", "tags", "city")
	readonly_fields = ("created_at", "updated_at")
	filter_horizontal = ("tags",)
	actions = ["approve_restaurants", "reject_restaurants"]

	@admin.action(description="Approve selected restaurants")
	def approve_restaurants(self, request, queryset):
		count = queryset.update(approval_status=Restaurant.ApprovalStatus.APPROVED)
		self.message_user(request, f"{count} restaurant(s) approved.")

	@admin.action(description="Reject selected restaurants")
	def reject_restaurants(self, request, queryset):
		count = queryset.update(approval_status=Restaurant.ApprovalStatus.REJECTED)
		self.message_user(request, f"{count} restaurant(s) rejected.")


@admin.register(Cuisine)
class CuisineAdmin(admin.ModelAdmin):
	list_display = ("name", "slug")
	prepopulated_fields = {"slug": ("name",)}


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
	list_display = ("name", "slug")
	prepopulated_fields = {"slug": ("name",)}


@admin.register(MenuItem)
class MenuItemAdmin(admin.ModelAdmin):
	list_display = ("name", "restaurant", "category", "price", "is_recommended")
	list_filter = ("category", "is_recommended", "is_vegetarian", "is_gluten_free")
	search_fields = ("name", "restaurant__name")
