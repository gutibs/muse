from django.contrib import admin

from notifications.models import DeviceToken, DigestLog, NotificationJob


@admin.register(DeviceToken)
class DeviceTokenAdmin(admin.ModelAdmin):
	list_display = ("user", "platform", "last_seen_at")
	list_filter = ("platform",)
	search_fields = ("user__email", "user__username")


@admin.register(NotificationJob)
class NotificationJobAdmin(admin.ModelAdmin):
	"""Sólo lectura: la cola la escribe `notify()`, no una persona.

	Está en el admin para poder mirar por qué algo no llegó, que es la pregunta
	que se va a hacer siempre.
	"""

	list_display = ("kind", "recipient", "state", "attempts", "created_at")
	list_filter = ("state", "kind")
	search_fields = ("recipient__email", "recipient__username", "idempotency_key")
	readonly_fields = tuple(f.name for f in NotificationJob._meta.fields)

	def has_add_permission(self, request):
		return False


@admin.register(DigestLog)
class DigestLogAdmin(admin.ModelAdmin):
	list_display = ("user", "local_date", "item_count")
	search_fields = ("user__email", "user__username")
	readonly_fields = ("created_at",)
