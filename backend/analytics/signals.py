"""Eventos que emite el servidor.

Viven acá y no en `pins/signals.py` para que la dependencia apunte en una
sola dirección: analytics conoce a pins, pins no sabe que analytics existe.
Así el día que se saque la app, se saca entera.
"""

from django.db.models.signals import post_save
from django.dispatch import receiver

from analytics.models import Event
from analytics.services.ingest import record_event
from pins.models import Pin


@receiver(post_save, sender=Pin, dispatch_uid="analytics_save_to_map")
def record_save_to_map(sender, instance, created, **kwargs):
	"""Guardar un restaurante es un hecho puntual: sólo el alta cuenta.

	Si contara cada `save()`, corregir la reseña tres veces multiplicaría por
	tres el número que se le muestra a un tercero.
	"""
	if not created:
		return

	record_event(
		name=Event.Name.SAVE_TO_MAP,
		user=instance.user,
		restaurant=instance.restaurant,
		props={"status": instance.status},
	)
