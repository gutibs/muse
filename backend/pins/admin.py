from django.contrib import admin

from pins.models import Persona, Pin


@admin.register(Pin)
class PinAdmin(admin.ModelAdmin):
	list_display = ("user", "restaurant", "status", "rating", "visited_at", "updated_at")
	list_filter = ("status", "personas", "rating")
	search_fields = (
		"user__email",
		"user__username",
		"restaurant__name",
		"restaurant__city",
	)
	readonly_fields = ("created_at", "updated_at")
	filter_horizontal = ("personas",)


@admin.register(Persona)
class PersonaAdmin(admin.ModelAdmin):
	list_display = ("name", "slug", "icon", "color")
	prepopulated_fields = {"slug": ("name",)}
