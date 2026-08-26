"""Los errores de validación de contraseña salen en el idioma del usuario.

LANGUAGE_CODE es "es" y la API no tiene LocaleMiddleware, así que sin activar
el idioma a mano `validate_password` contesta siempre en español. En este flujo
está garantizado que se vea: es la pantalla donde alguien elige una contraseña
nueva, y la mitad del beta no habla español.
"""

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.services.password_reset import issue_code
from tests.factories import UserFactory

WEAK = "12345678"


def _confirm_with_language(user, code, language):
	return APIClient().post(
		reverse("password_reset_confirm"),
		{"email": user.email, "code": code, "newPassword": WEAK, "language": language},
		format="json",
	)


@pytest.mark.critical
@pytest.mark.django_db
@pytest.mark.parametrize(
	("language", "needle"),
	[
		("es", "demasiado común"),
		("en", "too common"),
		("it", "troppo comune"),
	],
)
def test_password_errors_come_back_in_the_requested_language(language, needle):
	user = UserFactory()
	code, _ = issue_code(user)

	resp = _confirm_with_language(user, code, language)

	assert resp.status_code == 400, resp.content
	messages = " ".join(resp.json()["newPassword"])
	assert needle in messages, messages


@pytest.mark.critical
@pytest.mark.django_db
def test_unknown_language_falls_back_without_breaking():
	user = UserFactory()
	code, _ = issue_code(user)

	resp = _confirm_with_language(user, code, "klingon")

	assert resp.status_code == 400, resp.content
	assert resp.json()["newPassword"]
