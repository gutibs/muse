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


class MonthlyVenueStat(models.Model):
	"""Agregado mensual por venue, sin dato personal adentro.

	Existe para que la retención no se lleve puesto el histórico de negocio:
	los eventos crudos se borran a los 14 meses (llevan user_id), y esto
	queda para siempre. El nombre del restaurante va copiado en la fila
	porque el FK es SET_NULL: si el restaurante se borra, el número de un
	mes cerrado no puede quedar sin dueño en el reporte.
	"""

	restaurant = models.ForeignKey(
		"restaurants.Restaurant",
		on_delete=models.SET_NULL,
		null=True,
		blank=True,
		related_name="monthly_stats",
	)
	restaurant_name = models.CharField(max_length=200, blank=True)
	# Primer día del mes.
	month = models.DateField()
	name = models.CharField(max_length=32, choices=Event.Name.choices)
	destination = models.CharField(max_length=20, choices=Event.Destination.choices, blank=True)
	# Bruto: un tap, un punto.
	count = models.PositiveIntegerField(default=0)
	# Un tap por persona, venue y día. Es el número que se muestra como
	# principal: "cinco taps del mismo usuario en un rato" es una persona
	# interesada, no cinco.
	deduped_count = models.PositiveIntegerField(default=0)
	# Personas distintas. Los eventos ya anonimizados no tienen a quién
	# contar y quedan afuera de este número, nunca del bruto.
	unique_users = models.PositiveIntegerField(default=0)

	class Meta:
		db_table = "analytics_monthly_venue_stat"
		ordering = ["-month", "restaurant_name"]
		constraints = [
			models.UniqueConstraint(
				fields=["restaurant", "restaurant_name", "month", "name", "destination"],
				name="unique_monthly_venue_stat",
			)
		]
		indexes = [models.Index(fields=["-month", "name"])]

	def __str__(self):
		return f"{self.restaurant_name} · {self.month:%Y-%m} · {self.name}"
