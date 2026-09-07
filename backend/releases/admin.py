from django.contrib import admin

from releases.models import AppVersion


@admin.register(AppVersion)
class AppVersionAdmin(admin.ModelAdmin):
	"""El único camino de escritura de la política de versiones.

	Subir `min_supported` bloquea a todo el que esté por debajo, sin salida más
	allá del link. Es una acción con consecuencias inmediatas sobre gente real,
	así que conviene que pase por acá y no por un script.
	"""

	list_display = ("platform", "min_supported", "latest", "store_url", "updated_at")
	list_editable = ("min_supported", "latest", "store_url")
	list_display_links = ("platform",)
