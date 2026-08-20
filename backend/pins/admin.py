from django.contrib import admin

from pins.models import Pin, SharedList


@admin.register(Pin)
class PinAdmin(admin.ModelAdmin):
	list_display = ("user", "restaurant", "status", "rating", "visited_at", "updated_at")
	list_filter = ("status", "tags", "rating")
	search_fields = (
		"user__email",
		"user__username",
		"restaurant__name",
		"restaurant__city",
	)
	readonly_fields = ("created_at", "updated_at")
	filter_horizontal = ("tags",)


@admin.register(SharedList)
class SharedListAdmin(admin.ModelAdmin):
	list_display = ("user", "title", "status_filter", "is_active", "token", "created_at")
	list_filter = ("is_active", "status_filter")
	readonly_fields = ("token", "created_at")
