"""Cambiar la contraseña desde adentro no puede dejarte afuera.

Con CHECK_REVOKE_TOKEN activo, cambiar la contraseña mata todos los tokens
firmados con el hash anterior — incluido el del dispositivo desde el que
estás cambiándola. Sin devolver un par nuevo, el usuario ve "contraseña
actualizada" y la siguiente llamada lo escupe al login.
"""

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from tests.factories import UserFactory

OLD = "test-pass-123"
NEW = "Nu3va-clave-segura!"


def _auth_client(username, password=OLD):
	tokens = (
		APIClient()
		.post(reverse("token_obtain"), {"username": username, "password": password}, format="json")
		.json()
	)
	return APIClient(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}"), tokens


@pytest.mark.critical
@pytest.mark.django_db
def test_change_password_returns_a_working_token_pair():
	user = UserFactory(username="chg", email="chg@example.com")
	client, _ = _auth_client(user.username)

	resp = client.post(
		reverse("change_password"), {"currentPassword": OLD, "newPassword": NEW}, format="json"
	)

	assert resp.status_code == 200, resp.content
	body = resp.json()
	assert "access" in body and "refresh" in body, body

	fresh = APIClient(HTTP_AUTHORIZATION=f"Bearer {body['access']}")
	assert fresh.get(reverse("profile")).status_code == 200

	refreshed = APIClient().post(
		reverse("token_refresh"), {"refresh": body["refresh"]}, format="json"
	)
	assert refreshed.status_code == 200, refreshed.content


@pytest.mark.critical
@pytest.mark.django_db
def test_change_password_still_kills_the_other_devices():
	"""Lo que sí tiene que seguir pasando: las otras sesiones se cierran."""
	user = UserFactory(username="chg", email="chg@example.com")
	other_device, other_tokens = _auth_client(user.username)
	client, _ = _auth_client(user.username)

	client.post(
		reverse("change_password"), {"currentPassword": OLD, "newPassword": NEW}, format="json"
	)

	assert other_device.get(reverse("profile")).status_code == 401
	stale_refresh = APIClient().post(
		reverse("token_refresh"), {"refresh": other_tokens["refresh"]}, format="json"
	)
	assert stale_refresh.status_code == 401
