from django.contrib import admin
from django.contrib.gis import admin as gis_admin

from restaurants.models import Cuisine, MenuItem, Restaurant, Tag


@admin.register(Restaurant)
class RestaurantAdmin(gis_admin.GISModelAdmin):
	list_display = (
		"name",
		"city",
		"country",
		"cuisines_display",
		"approval_status",
		"created_by",
		"created_at",
	)
	search_fields = ("name", "city", "country", "address")
	list_filter = ("approval_status", "cuisines", "price_level", "quality_level", "tags", "city")
	readonly_fields = ("created_at", "updated_at")
	filter_horizontal = ("cuisines", "tags")

	def cuisines_display(self, obj):
		return ", ".join(c.name for c in obj.cuisines.all())

	cuisines_display.short_description = "Cuisines"
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
	list_display = ("name", "slug", "kind")
	list_filter = ("kind",)
	prepopulated_fields = {"slug": ("name",)}


@admin.register(MenuItem)
class MenuItemAdmin(admin.ModelAdmin):
	list_display = ("name", "restaurant", "category", "price", "tags_display")
	list_filter = ("category", "tags")
	search_fields = ("name", "restaurant__name")
	filter_horizontal = ("tags",)

	def tags_display(self, obj):
		return ", ".join(t.name for t in obj.tags.all())

	tags_display.short_description = "Tags"
