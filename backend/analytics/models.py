"""Eventos de producto.

No reusamos `feed.Activity`: sus verbs son un set cerrado pensado para el
feed social y `Activity.pin` es CASCADE, así que despinear un restaurante
borraría el evento retroactivamente. Una evidencia de negociación que
desaparece cuando el usuario cambia de opinión no sirve de evidencia.

`user` es SET_NULL y nunca CASCADE por la misma razón que las reseñas
sobreviven al borrado de cuenta (D-009): el borrado anonimiza, no destruye.
Ver `analytics/services/anonymise.py`.
"""

from django.conf import settings
from django.db import models


class Event(models.Model):
	class Name(models.TextChoices):
		SAVE_TO_MAP = "save_to_map", "Saved to map"
		VENUE_CARD_VIEW = "venue_card_view", "Venue card viewed"
		VENUE_DETAIL_VIEW = "venue_detail_view", "Venue detail viewed"
		EXTERNAL_ACTION_CLICK = "external_action_click", "External action clicked"

	class Destination(models.TextChoices):
		DIRECTIONS = "directions", "Directions"
		RESERVATION = "reservation", "Reservation"
		WEBSITE = "website", "Website"

	user = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.SET_NULL,
		null=True,
		blank=True,
		related_name="analytics_events",
	)
	name = models.CharField(max_length=32, choices=Name.choices)
	restaurant = models.ForeignKey(
		"restaurants.Restaurant",
		on_delete=models.SET_NULL,
		null=True,
		blank=True,
		related_name="analytics_events",
	)
	destination = models.CharField(max_length=20, choices=Destination.choices, blank=True)
	props = models.JSONField(default=dict, blank=True)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		db_table = "analytics_event"
		ordering = ["-created_at"]
		indexes = [
			# El primero sirve los totales del dashboard; el segundo es el que
			# hace barato "clicks a reservas por venue por mes", que es
			# literalmente el reporte que se pidió.
			models.Index(fields=["name", "-created_at"]),
			models.Index(fields=["restaurant", "name", "-created_at"]),
		]

	def __str__(self):
		return f"{self.name} · {self.restaurant or '—'} · {self.created_at:%Y-%m-%d}"
