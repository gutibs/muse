from django.contrib import admin

from analytics.models import Event


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
	list_display = ("name", "restaurant", "destination", "user", "created_at")
	list_filter = ("name", "destination")
	search_fields = ("restaurant__name",)
	date_hierarchy = "created_at"
	readonly_fields = ("name", "restaurant", "destination", "user", "props", "created_at")
	list_select_related = ("restaurant", "user")

	def has_add_permission(self, request):
		# Los eventos los escribe el producto, no una persona: un evento
		# cargado a mano contamina el número que se le muestra a un tercero.
		return False
