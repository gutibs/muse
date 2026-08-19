"""Retención de los eventos crudos.

14 meses: el estándar de facto para analytics bajo GDPR, y el mínimo que
permite comparar un mes contra el mismo mes del año anterior. Lo que se
conserva para siempre es el agregado mensual, que no tiene user_id.

La ventana está acá y no es parámetro de la operación: es lo que declara la
política de privacidad, no una perilla de mantenimiento.
"""

import datetime as dt
import logging

from django.utils import timezone

from analytics.models import Event
from analytics.services.reports import as_datetime, month_start, next_month, rollup_month

logger = logging.getLogger(__name__)

RETENTION = dt.timedelta(days=425)  # ~14 meses


def prune_events(now: dt.datetime | None = None) -> int:
	"""Consolida y recién después borra. Devuelve cuántos eventos se borraron.

	El orden no es un detalle: borrar antes de consolidar pierde el número
	para siempre, y no hay de dónde recalcularlo.

	Se borra por meses enteros, nunca la primera mitad de un mes. Un mes
	purgado a medias volvería a consolidarse más tarde sobre los eventos que
	quedaron, y el agregado —que se conserva para siempre— pasaría a decir
	menos de lo que pasó. El costo es tener hasta un mes más de eventos de
	los estrictamente necesarios.
	"""
	cutoff_month = month_start(((now or timezone.now()) - RETENTION).date())
	expired = Event.objects.filter(created_at__lt=as_datetime(cutoff_month))
	first = expired.order_by("created_at").first()
	if first is None:
		return 0

	month = month_start(first.created_at.date())
	while month < cutoff_month:
		rollup_month(month)
		month = next_month(month)

	deleted, _ = expired.delete()
	logger.info("Pruned %s analytics events older than %s days", deleted, RETENTION.days)
	return deleted
