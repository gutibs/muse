"""`prune_activity --days` no puede borrar la tabla entera por un valor degenerado.

El comando está pensado para correr desde un cron que templatea `--days` desde
una env var. Si esa var queda vacía o mal expandida, el comando corría como
`--days 0`: el cutoff quedaba en `now`, `created_at__lt=cutoff` matcheaba todo,
y el feed de todos los usuarios se borraba con exit 0 y un SUCCESS verde.
"""

from datetime import timedelta
from io import StringIO

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.utils import timezone

from feed.models import Activity
from pins.models import Pin
from tests.factories import PinFactory, RestaurantFactory, UserFactory


def _activity_aged(days_old):
	"""Crea una Activity y le fuerza `created_at` (auto_now_add ignora el kwarg)."""
	pin = PinFactory(user=UserFactory(), restaurant=RestaurantFactory(), status=Pin.Status.TO_VISIT)
	activity = Activity.objects.filter(pin=pin).first()
	Activity.objects.filter(pk=activity.pk).update(
		created_at=timezone.now() - timedelta(days=days_old)
	)
	return activity


@pytest.mark.django_db
@pytest.mark.parametrize("days", [0, -1, -30])
def test_prune_rejects_non_positive_days(days):
	_activity_aged(1)
	count_before = Activity.objects.count()

	with pytest.raises(CommandError):
		call_command("prune_activity", days=days, stdout=StringIO())

	assert Activity.objects.count() == count_before, "Un --days inválido no debe borrar nada"


@pytest.mark.django_db
def test_prune_deletes_only_rows_older_than_cutoff():
	old = _activity_aged(100)
	recent = _activity_aged(10)

	call_command("prune_activity", days=90, stdout=StringIO())

	assert not Activity.objects.filter(pk=old.pk).exists()
	assert Activity.objects.filter(pk=recent.pk).exists()


@pytest.mark.django_db
def test_prune_with_min_retention_keeps_todays_rows():
	"""`--days 1` es el mínimo aceptado y no toca lo de hoy."""
	fresh = _activity_aged(0)

	call_command("prune_activity", days=1, stdout=StringIO())

	assert Activity.objects.filter(pk=fresh.pk).exists()
