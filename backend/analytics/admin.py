from django.contrib import admin
from django.core.cache import cache
from django.shortcuts import render
from django.urls import path

from analytics.models import Event, MonthlyVenueStat
from analytics.services.reports import external_clicks_by_venue, summary

# El dashboard agrega sobre la tabla de eventos, que es la que más crece. Diez
# minutos de caché lo dejan lo bastante fresco para mirarlo varias veces
# seguidas sin repetir el escaneo.
DASHBOARD_CACHE_KEY = "analytics:dashboard"
DASHBOARD_CACHE_SECONDS = 600


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
	list_display = ("name", "restaurant", "destination", "user", "created_at")
	list_filter = ("name", "destination")
	search_fields = ("restaurant__name",)
	date_hierarchy = "created_at"
	readonly_fields = ("name", "restaurant", "destination", "user", "props", "created_at")
	list_select_related = ("restaurant", "user")
	change_list_template = "admin/analytics/event_changelist.html"

	def has_add_permission(self, request):
		# Los eventos los escribe el producto, no una persona: un evento
		# cargado a mano contamina el número que se le muestra a un tercero.
		return False

	def get_urls(self):
		"""El dashboard cuelga del changelist en vez de pisar `admin/index.html`.

		Sobrescribir el index obliga a mantener una copia del template de
		Django, que cambia entre versiones. Esto es una URL más y no rompe
		nada de lo que ya está.
		"""
		return [
			path(
				"dashboard/",
				self.admin_site.admin_view(self.dashboard_view),
				name="analytics_dashboard",
			),
			*super().get_urls(),
		]

	def dashboard_view(self, request):
		data = cache.get(DASHBOARD_CACHE_KEY)
		if data is None:
			data = {
				"summary": summary(),
				"clicks": external_clicks_by_venue(),
			}
			cache.set(DASHBOARD_CACHE_KEY, data, DASHBOARD_CACHE_SECONDS)

		context = {
			**self.admin_site.each_context(request),
			"title": "Analytics",
			**data,
		}
		return render(request, "admin/analytics/dashboard.html", context)


@admin.register(MonthlyVenueStat)
class MonthlyVenueStatAdmin(admin.ModelAdmin):
	list_display = (
		"month",
		"restaurant_name",
		"name",
		"destination",
		"deduped_count",
		"count",
		"unique_users",
	)
	list_filter = ("name", "destination", "month")
	search_fields = ("restaurant_name",)
	readonly_fields = tuple(f.name for f in MonthlyVenueStat._meta.fields if f.name != "id")

	def has_add_permission(self, request):
		return False
