"""RF17 — la limpieza de códigos vencidos o usados.

La tabla guarda hashes de credenciales: dejarla crecer para siempre es
acumular material sensible que ya no sirve para nada.
"""

from datetime import timedelta
from io import StringIO

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.utils import timezone

from accounts.models import PasswordResetCode
from accounts.services.password_reset import issue_code
from tests.factories import UserFactory


def _make(user, *, age_days, used=False, expired=True):
	created = timezone.now() - timedelta(days=age_days)
	entry = PasswordResetCode.objects.create(
		user=user,
		code_hash="not-a-real-hash",
		expires_at=created if expired else timezone.now() + timedelta(minutes=15),
		used_at=created if used else None,
	)
	# created_at es auto_now_add: se corrige con un UPDATE directo.
	PasswordResetCode.objects.filter(pk=entry.pk).update(created_at=created)
	entry.refresh_from_db()
	return entry


@pytest.mark.critical
@pytest.mark.django_db
def test_prune_deletes_only_expired_or_used_rows_older_than_30_days():
	user = UserFactory()
	old_expired = _make(user, age_days=31)
	old_used = _make(user, age_days=40, used=True)
	recent_expired = _make(user, age_days=3)
	live = _make(user, age_days=0, expired=False)

	call_command("prune_password_reset_codes", stdout=StringIO())

	surviving = set(PasswordResetCode.objects.values_list("pk", flat=True))
	assert old_expired.pk not in surviving
	assert old_used.pk not in surviving
	assert recent_expired.pk in surviving
	assert live.pk in surviving


@pytest.mark.critical
@pytest.mark.django_db
def test_prune_never_touches_a_live_code():
	"""El caso que rompe el producto: borrar el código de alguien que lo está
	tipeando. Un código vigente no tiene edad suficiente para calificar, pero
	el test lo fija por si el filtro cambia."""
	user = UserFactory()
	code, _ = issue_code(user)
	PasswordResetCode.objects.filter(user=user).update(
		created_at=timezone.now() - timedelta(days=365)
	)

	call_command("prune_password_reset_codes", stdout=StringIO())

	assert PasswordResetCode.objects.filter(user=user).exists()
	entry = PasswordResetCode.objects.get(user=user)
	assert entry.expires_at > timezone.now()
	assert code  # el valor sigue siendo canjeable


@pytest.mark.critical
@pytest.mark.django_db
def test_prune_refuses_a_zero_or_negative_retention():
	"""Mismo blindaje que prune_activity: una env var vacía en el cron pone
	--days en 0 y se lleva puesta la tabla entera con exit 0."""
	with pytest.raises(CommandError):
		call_command("prune_password_reset_codes", "--days", "0", stdout=StringIO())
