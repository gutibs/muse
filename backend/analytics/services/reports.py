"""Agregados. Nada de esto vive en una view.

Dos cifras conviven a propósito para cada corte:

- `count` es el bruto, un tap un punto.
- `deduped_count` cuenta un tap por persona, venue y día.

Se guardan las dos porque el número termina delante de un tercero —"cuánta
gente tocó reservar en este restaurante"— y hay que poder responder qué se
está mostrando. La deduplicada es la que se muestra primero; el bruto está
al lado para que la pregunta tenga respuesta.
"""

import datetime as dt

from django.db.models import Count, Q
from django.db.models.functions import TruncDate
from django.utils import timezone

from analytics.models import Event, MonthlyVenueStat

# Corte para los totales de la portada del dashboard.
SUMMARY_WINDOW = dt.timedelta(days=30)


def month_start(day: dt.date) -> dt.date:
	return day.replace(day=1)


def as_datetime(day: dt.date) -> dt.datetime:
	"""Medianoche de `day` en la zona del proyecto.

	Comparar `created_at` contra un `date` pelado deja que Django lo
	interprete como naive, y el borde del mes se corre las horas del offset.
	"""
	return timezone.make_aware(dt.datetime.combine(day, dt.time.min))


def next_month(month: dt.date) -> dt.date:
	return (month.replace(day=28) + dt.timedelta(days=7)).replace(day=1)


def aggregate_events(queryset) -> list[dict]:
	"""Agrupa por (venue, evento, destino) contando bruto, dedup y personas.

	El dedup por (persona, venue, día) se arma en Python sobre un
	`values().distinct()` en vez de en SQL: son cuatro campos y un DISTINCT
	sobre agregación anidada, y esto corre en un cron mensual, no en un
	request.
	"""
	rows: dict[tuple, dict] = {}

	base = queryset.annotate(day=TruncDate("created_at")).values(
		"restaurant_id",
		"restaurant__name",
		"name",
		"destination",
		"user_id",
		"day",
	)

	for row in base.annotate(hits=Count("id")):
		key = (row["restaurant_id"], row["restaurant__name"], row["name"], row["destination"])
		bucket = rows.setdefault(
			key,
			{
				"restaurant_id": row["restaurant_id"],
				"restaurant_name": row["restaurant__name"] or "",
				"name": row["name"],
				"destination": row["destination"],
				"count": 0,
				"deduped_count": 0,
				"people": set(),
			},
		)
		bucket["count"] += row["hits"]
		# Una fila de este loop ya es (persona, venue, día): contarla como 1
		# es exactamente la definición de dedupe que se acordó.
		bucket["deduped_count"] += 1
		if row["user_id"] is not None:
			bucket["people"].add(row["user_id"])

	return [
		{**bucket, "unique_users": len(bucket.pop("people"))}
		for bucket in sorted(rows.values(), key=lambda b: -b["count"])
	]


def rollup_month(day: dt.date) -> int:
	"""Consolida el mes que contiene `day`. Idempotente.

	Un agregado nunca baja. Si el mes ya estaba consolidado y sus eventos
	crudos fueron purgados, volver a correr esto encontraría menos filas de
	las que hubo: el agregado es el registro definitivo de un mes cerrado, no
	un reflejo de lo que quede en la tabla de eventos.
	"""
	start = month_start(day)
	end = next_month(start)
	events = Event.objects.filter(
		created_at__gte=as_datetime(start), created_at__lt=as_datetime(end)
	)

	written = 0
	for bucket in aggregate_events(events):
		stat, _ = MonthlyVenueStat.objects.get_or_create(
			restaurant_id=bucket["restaurant_id"],
			restaurant_name=bucket["restaurant_name"],
			month=start,
			name=bucket["name"],
			destination=bucket["destination"],
		)
		stat.count = max(stat.count, bucket["count"])
		stat.deduped_count = max(stat.deduped_count, bucket["deduped_count"])
		stat.unique_users = max(stat.unique_users, bucket["unique_users"])
		stat.save(update_fields=["count", "deduped_count", "unique_users"])
		written += 1
	return written


def summary(window: dt.timedelta = SUMMARY_WINDOW) -> dict[str, int]:
	"""Los números de la portada, sobre los últimos 30 días."""
	since = timezone.now() - window
	events = Event.objects.filter(created_at__gte=since)
	return events.aggregate(
		saves=Count("id", filter=Q(name=Event.Name.SAVE_TO_MAP)),
		card_views=Count("id", filter=Q(name=Event.Name.VENUE_CARD_VIEW)),
		detail_views=Count("id", filter=Q(name=Event.Name.VENUE_DETAIL_VIEW)),
		external_clicks=Count("id", filter=Q(name=Event.Name.EXTERNAL_ACTION_CLICK)),
		people=Count("user", distinct=True),
	)


def external_clicks_by_venue(months: int = 12) -> list[dict]:
	"""Clicks externos por venue y por mes, que es el reporte del bloque.

	Sale de los agregados para los meses ya consolidados y del crudo para el
	mes en curso, así el mes corriente no aparece vacío hasta que corra el
	cron.
	"""
	today = timezone.now().date()
	current = month_start(today)
	first = current
	for _ in range(months - 1):
		first = month_start(first - dt.timedelta(days=1))

	rows = [
		{
			"month": stat.month,
			"restaurant_name": stat.restaurant_name,
			"destination": stat.destination,
			"count": stat.count,
			"deduped_count": stat.deduped_count,
			"unique_users": stat.unique_users,
		}
		for stat in MonthlyVenueStat.objects.filter(
			name=Event.Name.EXTERNAL_ACTION_CLICK,
			month__gte=first,
			month__lt=current,
		)
	]

	live = Event.objects.filter(
		name=Event.Name.EXTERNAL_ACTION_CLICK,
		created_at__gte=as_datetime(current),
	)
	rows.extend(
		{
			"month": current,
			"restaurant_name": bucket["restaurant_name"],
			"destination": bucket["destination"],
			"count": bucket["count"],
			"deduped_count": bucket["deduped_count"],
			"unique_users": bucket["unique_users"],
		}
		for bucket in aggregate_events(live)
	)

	return sorted(rows, key=lambda r: (-r["month"].toordinal(), -r["count"]))
