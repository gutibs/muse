"""RF2 — la petición de código responde siempre lo mismo.

El requisito existe para cerrar la enumeración de cuentas: si el status o el
cuerpo cambian según exista o no la cuenta —o según Resend esté caído—, ese
endpoint anónimo dice quién tiene cuenta en Muse. Ver docs/SPEC_RESET_PASSWORD.md.
"""

import logging
from unittest.mock import patch

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.models import PasswordResetCode
from accounts.services.email import EmailSendError
from accounts.views import PASSWORD_RESET_ACCEPTED
from tests.factories import UserFactory

EXISTING_EMAIL = "reset-me@example.com"
MISSING_EMAIL = "nobody-here@example.com"


@pytest.mark.critical
@pytest.mark.django_db
@patch("accounts.services.password_reset.send_password_reset_email")
def test_request_response_is_identical_for_existing_missing_and_failing_send(send):
	"""Los tres escenarios de RF2, comparados byte a byte."""
	UserFactory(username="reset-me", email=EXISTING_EMAIL)
	url = reverse("password_reset")

	send.return_value = {"id": "re_ok"}
	existing = APIClient().post(url, {"email": EXISTING_EMAIL}, format="json")

	missing = APIClient().post(url, {"email": MISSING_EMAIL}, format="json")

	send.side_effect = EmailSendError("Resend unreachable", status_code=502)
	failing = APIClient().post(url, {"email": EXISTING_EMAIL}, format="json")

	assert existing.status_code == 200, existing.content
	assert missing.status_code == existing.status_code, missing.content
	assert failing.status_code == existing.status_code, failing.content
	assert missing.content == existing.content
	assert failing.content == existing.content


@pytest.mark.critical
@pytest.mark.django_db
@patch("accounts.services.password_reset.send_password_reset_email")
def test_request_for_existing_account_creates_one_code_and_sends_once(send):
	"""RF1: la aceptación del camino feliz, que da sentido al de arriba."""
	user = UserFactory(username="reset-me", email=EXISTING_EMAIL)
	send.return_value = {"id": "re_ok"}

	APIClient().post(reverse("password_reset"), {"email": EXISTING_EMAIL}, format="json")

	assert PasswordResetCode.objects.filter(user=user).count() == 1
	send.assert_called_once()


@pytest.mark.critical
@pytest.mark.django_db
@patch("accounts.services.password_reset.send_password_reset_email")
def test_request_for_unknown_email_creates_no_row_and_sends_nothing(send):
	APIClient().post(reverse("password_reset"), {"email": MISSING_EMAIL}, format="json")

	assert PasswordResetCode.objects.count() == 0
	send.assert_not_called()


@pytest.mark.critical
@pytest.mark.django_db
@patch("accounts.services.password_reset.make_password")
@patch("accounts.services.password_reset.send_password_reset_email")
def test_unknown_email_still_pays_for_a_hash(send, make_password_mock):
	"""RF3: el hasheo es lo más caro del request. Si el camino sin cuenta se
	lo saltea, el tiempo de respuesta dice quién tiene cuenta."""
	make_password_mock.return_value = "fake-hash"

	APIClient().post(reverse("password_reset"), {"email": MISSING_EMAIL}, format="json")

	make_password_mock.assert_called_once()
	send.assert_not_called()


@pytest.mark.critical
@pytest.mark.django_db
@patch("accounts.services.password_reset.send_password_reset_email")
def test_fourth_request_within_the_hour_sends_nothing(send):
	"""RF4: tope por casilla destino. Sin esto, el throttle por IP no impide
	inundar el buzón de otra persona ni pedir códigos en serie."""
	user = UserFactory(username="reset-me", email=EXISTING_EMAIL)
	send.return_value = {"id": "re_ok"}
	url = reverse("password_reset")

	for _ in range(3):
		APIClient().post(url, {"email": EXISTING_EMAIL}, format="json")

	assert send.call_count == 3
	assert PasswordResetCode.objects.filter(user=user).count() == 3

	fourth = APIClient().post(url, {"email": EXISTING_EMAIL}, format="json")

	assert send.call_count == 3, "el cuarto pedido no debe enviar nada"
	assert PasswordResetCode.objects.filter(user=user).count() == 3
	# Y aun así responde lo mismo que los tres anteriores (RF2).
	assert fourth.status_code == 200
	assert fourth.json() == {"detail": PASSWORD_RESET_ACCEPTED["detail"]}


@pytest.mark.critical
@pytest.mark.django_db
@patch("accounts.services.password_reset.send_password_reset_email")
def test_failed_send_leaves_the_row_marked_as_unsent_and_logs_it(send, caplog):
	"""RF5: la fila queda para reenviar a mano y el fallo deja traza."""
	user = UserFactory(username="reset-me", email=EXISTING_EMAIL)
	send.side_effect = EmailSendError("Resend unreachable", status_code=502)

	with caplog.at_level(logging.ERROR, logger="accounts.services.password_reset"):
		APIClient().post(reverse("password_reset"), {"email": EXISTING_EMAIL}, format="json")

	entry = PasswordResetCode.objects.get(user=user)
	assert entry.sent_at is None
	assert any(r.levelno == logging.ERROR for r in caplog.records)


@pytest.mark.critical
@pytest.mark.django_db
@patch("accounts.services.password_reset.send_password_reset_email")
def test_successful_send_marks_the_row_as_sent(send):
	user = UserFactory(username="reset-me", email=EXISTING_EMAIL)
	send.return_value = {"id": "re_ok"}

	APIClient().post(reverse("password_reset"), {"email": EXISTING_EMAIL}, format="json")

	assert PasswordResetCode.objects.get(user=user).sent_at is not None
