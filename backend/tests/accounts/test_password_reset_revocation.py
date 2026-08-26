"""RF13 — resetear la contraseña cierra las sesiones abiertas.

Quien resetea porque sospecha que le tomaron la cuenta necesita que el
atacante quede afuera. Sin esto, un access o un refresh robado sobrevive al
reset y el reset no sirve para lo que la gente lo usa.
Ver docs/SPEC_RESET_PASSWORD.md RF13 y "Compatibilidad" en §4.
"""

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.services.password_reset import issue_code
from tests.factories import UserFactory

OLD_PASSWORD = "test-pass-123"
NEW_PASSWORD = "Nu3va-clave-segura!"


def _tokens(email, password):
	resp = APIClient().post(
		reverse("token_obtain"), {"username": email, "password": password}, format="json"
	)
	assert resp.status_code == 200, resp.content
	return resp.json()


def _reset(user):
	code, _ = issue_code(user)
	resp = APIClient().post(
		reverse("password_reset_confirm"),
		{"email": user.email, "code": code, "newPassword": NEW_PASSWORD},
		format="json",
	)
	assert resp.status_code == 200, resp.content


@pytest.mark.critical
@pytest.mark.django_db
def test_access_token_issued_before_the_reset_is_rejected_afterwards():
	user = UserFactory(username="revoke-me", email="revoke-me@example.com")
	old = _tokens(user.username, OLD_PASSWORD)["access"]

	before = APIClient(HTTP_AUTHORIZATION=f"Bearer {old}").get(reverse("profile"))
	assert before.status_code == 200, before.content

	_reset(user)

	after = APIClient(HTTP_AUTHORIZATION=f"Bearer {old}").get(reverse("profile"))
	assert after.status_code == 401, after.content


@pytest.mark.critical
@pytest.mark.django_db
def test_refresh_token_issued_before_the_reset_is_rejected_afterwards():
	user = UserFactory(username="revoke-me", email="revoke-me@example.com")
	old_refresh = _tokens(user.username, OLD_PASSWORD)["refresh"]

	_reset(user)

	refreshed = APIClient().post(reverse("token_refresh"), {"refresh": old_refresh}, format="json")
	assert refreshed.status_code == 401, refreshed.content


@pytest.mark.critical
@pytest.mark.django_db
def test_token_issued_after_the_reset_works():
	user = UserFactory(username="revoke-me", email="revoke-me@example.com")
	_reset(user)

	new_access = _tokens(user.username, NEW_PASSWORD)["access"]
	resp = APIClient(HTTP_AUTHORIZATION=f"Bearer {new_access}").get(reverse("profile"))
	assert resp.status_code == 200, resp.content
