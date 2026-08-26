"""RF8 — cinco intentos por código, contados de forma atómica.

Seis dígitos son 10^6 combinaciones: el tope de intentos es lo que hace que
el espacio alcance. Si el contador se pierde bajo concurrencia, cinco requests
simultáneas valen un intento y el tope deja de existir.
Ver docs/SPEC_RESET_PASSWORD.md RF8.
"""

import logging
import threading
from datetime import timedelta
from unittest.mock import patch

import pytest
from django.db import connection
from django.urls import reverse
from django.utils import timezone
from rest_framework.exceptions import ValidationError
from rest_framework.test import APIClient

from accounts.models import PasswordResetCode
from accounts.services.password_reset import confirm_reset, issue_code
from tests.factories import UserFactory

NEW_PASSWORD = "Nu3va-clave-segura!"
WRONG_CODE = "000000"


def _age(user, *, minutes):
	"""Corre el reloj hacia atrás sobre la fila: emitida hace `minutes`."""
	entry = PasswordResetCode.objects.get(user=user)
	entry.expires_at = timezone.now() + timedelta(minutes=PasswordResetCode.TTL_MINUTES - minutes)
	entry.save(update_fields=["expires_at"])


def _confirm(email, code, password=NEW_PASSWORD):
	return APIClient().post(
		reverse("password_reset_confirm"),
		{"email": email, "code": code, "newPassword": password},
		format="json",
	)


@pytest.mark.critical
@pytest.mark.django_db
def test_four_failed_attempts_leave_the_code_usable():
	user = UserFactory()
	code = issue_code(user)

	for _ in range(4):
		failed = _confirm(user.email, WRONG_CODE)
		assert failed.status_code == 400, failed.content

	assert PasswordResetCode.objects.get(user=user).attempts == 4

	ok = _confirm(user.email, code)
	assert ok.status_code == 200, ok.content
	user.refresh_from_db()
	assert user.check_password(NEW_PASSWORD)


@pytest.mark.critical
@pytest.mark.django_db
def test_fifth_failed_attempt_burns_the_code_even_with_the_right_value():
	user = UserFactory()
	code = issue_code(user)

	for _ in range(5):
		_confirm(user.email, WRONG_CODE)

	burned = _confirm(user.email, code)
	assert burned.status_code == 400, burned.content
	user.refresh_from_db()
	assert not user.check_password(NEW_PASSWORD)


@pytest.mark.critical
@pytest.mark.slow
@pytest.mark.django_db(transaction=True)
def test_five_concurrent_failed_attempts_all_count():
	"""Cinco hilos entran juntos a la barrera y fallan a la vez. Con un
	read-modify-write desde Python los incrementos se pisan y el contador
	queda por debajo de cinco; con F() en la base, no."""
	user = UserFactory()
	issue_code(user)

	barrier = threading.Barrier(5)
	rejections = []

	def attempt():
		try:
			barrier.wait(timeout=5)
			try:
				confirm_reset(email=user.email, code=WRONG_CODE, new_password=NEW_PASSWORD)
			except ValidationError as exc:
				# El rechazo es el resultado esperado; se junta para verificar
				# que los cinco hilos llegaron a intentar de verdad.
				rejections.append(exc)
		finally:
			connection.close()

	threads = [threading.Thread(target=attempt) for _ in range(5)]
	for t in threads:
		t.start()
	for t in threads:
		t.join(timeout=15)

	assert len(rejections) == 5, "los cinco hilos tienen que haber intentado y fallado"
	assert PasswordResetCode.objects.get(user=user).attempts == 5


@pytest.mark.critical
@pytest.mark.django_db
@patch("accounts.services.password_reset._random_code", return_value="424242")
def test_two_users_with_the_same_live_code_cannot_reach_each_other(_random):
	"""RF6: la búsqueda va por usuario y después por código, nunca por código
	solo. Con 10^6 valores y códigos vivos de a muchos, la colisión ocurre."""
	alice = UserFactory(username="alice", email="alice@example.com")
	bob = UserFactory(username="bob", email="bob@example.com")
	issue_code(alice)
	issue_code(bob)

	ok = _confirm(alice.email, "424242")
	assert ok.status_code == 200, ok.content

	alice.refresh_from_db()
	bob.refresh_from_db()
	assert alice.check_password(NEW_PASSWORD)
	assert not bob.check_password(NEW_PASSWORD), "el canje de Alice no toca a Bob"
	assert PasswordResetCode.objects.get(user=bob).used_at is None


@pytest.mark.critical
@pytest.mark.django_db
def test_code_works_at_fourteen_minutes_and_not_at_sixteen():
	"""RF7: vigencia de 15 minutos."""
	early_user = UserFactory(username="early", email="early@example.com")
	early_code = issue_code(early_user)
	_age(early_user, minutes=14)
	early = _confirm(early_user.email, early_code)
	assert early.status_code == 200, early.content

	late_user = UserFactory(username="late", email="late@example.com")
	late_code = issue_code(late_user)
	_age(late_user, minutes=16)
	late = _confirm(late_user.email, late_code)
	assert late.status_code == 400, late.content
	late_user.refresh_from_db()
	assert not late_user.check_password(NEW_PASSWORD)


@pytest.mark.critical
@pytest.mark.django_db
def test_requesting_a_new_code_kills_the_previous_one():
	"""RF9: sin esto, RF7 y RF8 se esquivan pidiendo un código nuevo y
	siguiendo con el viejo."""
	user = UserFactory()
	first = issue_code(user)
	first_row = PasswordResetCode.objects.get(user=user)
	second = issue_code(user)

	# El anterior queda muerto en la base, no sólo tapado por el nuevo: si
	# sobreviviera vigente, quemar los 5 intentos del nuevo devolvería la
	# búsqueda al viejo y el tope de intentos se duplicaría.
	first_row.refresh_from_db()
	assert first_row.expires_at <= timezone.now()

	stale = _confirm(user.email, first)
	assert stale.status_code == 400, stale.content

	fresh = _confirm(user.email, second)
	assert fresh.status_code == 200, fresh.content


@pytest.mark.critical
@pytest.mark.django_db
def test_a_code_cannot_be_redeemed_twice():
	"""RF10: dentro de los 15 minutos, el segundo canje falla igual."""
	user = UserFactory()
	code = issue_code(user)

	first = _confirm(user.email, code)
	assert first.status_code == 200, first.content

	second = _confirm(user.email, code, password="Otra-clave-distinta-9!")
	assert second.status_code == 400, second.content
	user.refresh_from_db()
	assert user.check_password(NEW_PASSWORD), "la contraseña quedó la del primer canje"


@pytest.mark.critical
@pytest.mark.django_db
def test_the_plain_code_is_never_persisted(caplog):
	"""RF11: es una credencial. No va en claro en la fila ni en los logs."""
	user = UserFactory()
	with caplog.at_level(logging.DEBUG):
		code = issue_code(user)
		_confirm(user.email, WRONG_CODE)

	entry = PasswordResetCode.objects.get(user=user)
	row = {f.name: str(getattr(entry, f.name)) for f in PasswordResetCode._meta.fields}
	assert not any(code in value for value in row.values()), row
	assert not any(code in r.getMessage() for r in caplog.records)


@pytest.mark.critical
@pytest.mark.django_db
def test_new_password_must_pass_the_project_validators():
	"""RF12: si el reset es más permisivo que el registro, el registro no
	valida nada — alcanza con resetear para poner '12345678'."""
	user = UserFactory()
	code = issue_code(user)

	weak = _confirm(user.email, code, password="12345678")

	assert weak.status_code == 400, weak.content
	assert "newPassword" in weak.json(), weak.content
	user.refresh_from_db()
	assert not user.check_password("12345678")
