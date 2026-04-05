from django.apps import AppConfig


class PinsConfig(AppConfig):
	default_auto_field = "django.db.models.BigAutoField"
	name = "pins"

	def ready(self):
		import pins.signals  # noqa: F401
