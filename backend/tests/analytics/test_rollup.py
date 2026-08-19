"""Consolidación y purga.

Los eventos crudos llevan user_id y caducan a los 14 meses. Antes de irse
dejan un agregado mensual por venue que no tiene dato personal y se conserva:
si no, el día que caduque el primer mes, el histórico que se le muestra a un
tercero se achica solo y no hay forma de recuperarlo.

El orden importa y por eso está testeado: purgar antes de consolidar pierde
el número para siempre.
"""

from datetime import UTC, datetime, timedelta

import pytest

from analytics.models import Event, MonthlyVenueStat
from analytics.services.reports import rollup_month
from analytics.services.retention import RETENTION, prune_events
from tests.factories import RestaurantFactory, UserFactory


def _event_at(when, **kwargs):
	event = Event.objects.create(**kwargs)
	Event.objects.filter(pk=event.pk).update(created_at=when)
	event.refresh_from_db()
	return event


@pytest.mark.django_db
def test_rollup_counts_raw_deduped_and_people():
	restaurant = RestaurantFactory(name="Bar Nacional")
	someone, other = UserFactory(), UserFactory()
	day = datetime(2026, 3, 4, 12, 0, tzinfo=UTC)
	common = {
		"name": Event.Name.EXTERNAL_ACTION_CLICK,
		"restaurant": restaurant,
		"destination": Event.Destination.RESERVATION,
	}
	# Tres taps de la misma persona el mismo día: una sola intención.
	for _ in range(3):
		_event_at(day, user=someone, **common)
	# La misma persona, otro día: cuenta de nuevo.
	_event_at(day + timedelta(days=1), user=someone, **common)
	# Y otra persona.
	_event_at(day, user=other, **common)

	rollup_month(day.date())

	stat = MonthlyVenueStat.objects.get(name=Event.Name.EXTERNAL_ACTION_CLICK)
	assert stat.count == 5
	assert stat.deduped_count == 3
	assert stat.unique_users == 2
	assert stat.restaurant_name == "Bar Nacional"


@pytest.mark.django_db
def test_rollup_is_idempotent():
	"""Corre en un cron: repetirlo tiene que dar lo mismo, no el doble."""
	restaurant = RestaurantFactory()
	day = datetime(2026, 3, 4, 12, 0, tzinfo=UTC)
	_event_at(day, name=Event.Name.SAVE_TO_MAP, user=UserFactory(), restaurant=restaurant)

	rollup_month(day.date())
	rollup_month(day.date())

	assert MonthlyVenueStat.objects.count() == 1
	assert MonthlyVenueStat.objects.get().count == 1


@pytest.mark.django_db
def test_anonymised_events_still_count_but_not_as_people():
	restaurant = RestaurantFactory()
	day = datetime(2026, 3, 4, 12, 0, tzinfo=UTC)
	_event_at(day, name=Event.Name.SAVE_TO_MAP, user=None, restaurant=restaurant)

	rollup_month(day.date())

	stat = MonthlyVenueStat.objects.get()
	assert stat.count == 1
	assert stat.unique_users == 0


NOW = datetime(2026, 8, 19, 12, 0, tzinfo=UTC)


@pytest.mark.critical
@pytest.mark.django_db
def test_prune_consolidates_before_deleting():
	restaurant = RestaurantFactory(name="Bar Nacional")
	old = NOW - RETENTION - timedelta(days=45)
	_event_at(old, name=Event.Name.SAVE_TO_MAP, user=UserFactory(), restaurant=restaurant)

	deleted = prune_events(now=NOW)

	assert deleted == 1
	assert Event.objects.count() == 0
	stat = MonthlyVenueStat.objects.get()
	assert stat.count == 1
	assert stat.restaurant_name == "Bar Nacional"


@pytest.mark.critical
@pytest.mark.django_db
def test_prune_keeps_events_inside_the_window():
	restaurant = RestaurantFactory()
	recent = NOW - timedelta(days=30)
	_event_at(recent, name=Event.Name.SAVE_TO_MAP, user=UserFactory(), restaurant=restaurant)

	assert prune_events(now=NOW) == 0
	assert Event.objects.count() == 1


@pytest.mark.critical
@pytest.mark.django_db
def test_prune_never_deletes_half_a_month():
	"""Un mes purgado a medias se re-consolidaría más tarde sobre lo que
	quedó, y el agregado —que se guarda para siempre— pasaría a decir menos
	de lo que pasó. Se borran meses enteros o nada."""
	restaurant = RestaurantFactory()
	# El corte cae un 20 de junio: un evento del 19 ya pasó los 14 meses, pero
	# es del mismo mes que el corte y su mes todavía no está cerrado.
	cutoff = NOW - RETENTION
	assert cutoff.day > 1, "la fecha fijada del test tiene que caer dentro del mes"
	just_over = cutoff - timedelta(days=1)
	_event_at(just_over, name=Event.Name.SAVE_TO_MAP, user=UserFactory(), restaurant=restaurant)

	prune_events(now=NOW)

	assert Event.objects.count() == 1


@pytest.mark.django_db
def test_a_consolidated_month_does_not_shrink_when_rerun():
	restaurant = RestaurantFactory()
	day = datetime(2026, 3, 4, 12, 0, tzinfo=UTC)
	_event_at(day, name=Event.Name.SAVE_TO_MAP, user=UserFactory(), restaurant=restaurant)
	rollup_month(day.date())

	Event.objects.all().delete()
	rollup_month(day.date())

	assert MonthlyVenueStat.objects.get().count == 1
