"""Registrarse no dice si un email ya tiene cuenta.

Antes contestaba "A user with this email already exists" a cualquiera, así que
probando direcciones se armaba la lista de quién está en Muse. Cerrarlo obliga
a que la respuesta sea idéntica en los dos casos, y eso obliga a que el alta
deje de devolver sesión: los únicos tokens posibles para un email ya usado
serían los de esa cuenta, o sea regalarla.

El alta real ahora confirma por mail y se entra por el login de siempre.
"""

from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient

from tests.factories import UserFactory

User = get_user_model()

PAYLOAD = {
	"email": "nueva@example.com",
	"password": "Sup3r-strong-pass!",
	"displayName": "Nueva",
	"acceptPrivacy": True,
}


def _register(**overrides):
	return APIClient().post(reverse("register"), {**PAYLOAD, **overrides}, format="json")


@pytest.mark.critical
@pytest.mark.django_db
@patch("accounts.serializers.send_account_exists_email")
@patch("accounts.serializers.send_welcome_email")
def test_a_taken_email_answers_exactly_like_a_fresh_one(welcome, exists):
	UserFactory(username="taken", email="taken@example.com")

	fresh = _register()
	taken = _register(email="taken@example.com")

	assert fresh.status_code == taken.status_code
	assert (
		fresh.json() == taken.json()
	), f"distinguibles: nueva={fresh.json()} tomada={taken.json()}"


@pytest.mark.critical
@pytest.mark.django_db
@patch("accounts.serializers.send_account_exists_email")
@patch("accounts.serializers.send_welcome_email")
def test_registering_with_a_taken_email_creates_nothing(welcome, exists):
	existing = UserFactory(username="taken", email="taken@example.com")
	before = User.objects.count()

	_register(email="taken@example.com")

	assert User.objects.count() == before
	existing.refresh_from_db()
	assert existing.check_password("test-pass-123"), "la contraseña ajena no se toca"


@pytest.mark.critical
@pytest.mark.django_db
@patch("accounts.serializers.send_account_exists_email")
@patch("accounts.serializers.send_welcome_email")
def test_the_owner_of_a_taken_email_is_warned(welcome, exists):
	UserFactory(username="taken", email="taken@example.com")

	_register(email="taken@example.com")

	exists.assert_called_once()
	welcome.assert_not_called()


@pytest.mark.critical
@pytest.mark.django_db
@patch("accounts.serializers.send_account_exists_email")
@patch("accounts.serializers.send_welcome_email")
def test_a_real_signup_creates_the_account_and_welcomes_it(welcome, exists):
	resp = _register()

	assert resp.status_code == 202, resp.content
	user = User.objects.get(email="nueva@example.com")
	assert user.check_password("Sup3r-strong-pass!")
	welcome.assert_called_once()
	exists.assert_not_called()


@pytest.mark.critical
@pytest.mark.django_db
@patch("accounts.serializers.send_account_exists_email")
@patch("accounts.serializers.send_welcome_email")
def test_registering_never_returns_a_session(welcome, exists):
	"""Es la razón de que el alta cambie: con tokens en la respuesta, el caso
	del email tomado no puede ser idéntico sin entregar esa cuenta."""
	resp = _register()

	body = resp.content.decode()
	assert "access" not in body and "refresh" not in body, body


@pytest.mark.critical
@pytest.mark.django_db
@patch("accounts.serializers.send_account_exists_email")
@patch("accounts.serializers.send_welcome_email")
def test_the_new_account_can_log_in_right_away(welcome, exists):
	"""No hay verificación de email: la cuenta queda usable, el mail sólo
	confirma. Que el alta no loguee no puede convertirse en no poder entrar."""
	_register()

	tokens = APIClient().post(
		reverse("token_obtain"),
		{"username": "nueva@example.com", "password": "Sup3r-strong-pass!"},
		format="json",
	)

	assert tokens.status_code == 200, tokens.content
	assert "access" in tokens.json()


@pytest.mark.critical
@pytest.mark.django_db
@patch("accounts.serializers.send_account_exists_email")
@patch("accounts.serializers.send_welcome_email")
def test_a_failed_email_does_not_lose_the_account(welcome, exists, caplog):
	"""Si Resend está caído, la cuenta igual se crea: perder el alta por eso
	es peor que no mandar el mail."""
	from accounts.services.email import EmailSendError

	welcome.side_effect = EmailSendError("Resend caído", status_code=502)

	resp = _register()

	assert resp.status_code == 202, resp.content
	assert User.objects.filter(email="nueva@example.com").exists()
