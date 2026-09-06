"""Los errores de la API salen en el idioma que pide el cliente.

Probando el APK V1.3.0 el 2026-09-06, borrar la cuenta con la contraseña
equivocada respondía "Current password is incorrect." con la app entera en
español. No era ese mensaje: el backend no traducía ninguno de los 28 que un
usuario puede llegar a ver. `USE_I18N` estaba en True y `LANGUAGE_CODE` en
"es", pero ningún texto pasaba por gettext, así que esa configuración no hacía
nada.

Estos tests cubren las dos mitades que tienen que seguir puestas: que el
mecanismo funcione punta a punta, y que un mensaje nuevo no pueda nacer sin
`_()` sin que alguien se entere.
"""

import re
from pathlib import Path

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from tests.factories import UserFactory

PASSWORD = "test-pass-123"
BACKEND = Path(__file__).resolve().parent.parent


def _auth_client(user):
	tokens = (
		APIClient()
		.post(
			reverse("token_obtain"),
			{"username": user.username, "password": PASSWORD},
			format="json",
		)
		.json()
	)
	return APIClient(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")


@pytest.mark.django_db
@pytest.mark.parametrize(
	("header", "esperado"),
	[
		("en", "Current password is incorrect."),
		("es", "La contraseña actual no es correcta."),
		("it", "La password attuale non è corretta."),
		# Lo que manda un navegador de verdad: región y calidades. El
		# LocaleMiddleware tiene que resolverlo a "es".
		("es-AR,es;q=0.9,en;q=0.8", "La contraseña actual no es correcta."),
	],
)
def test_el_error_sale_en_el_idioma_pedido(header, esperado):
	user = UserFactory(password=PASSWORD)
	client = _auth_client(user)

	response = client.delete(
		reverse("profile"),
		{"currentPassword": "no-es-esta"},
		format="json",
		HTTP_ACCEPT_LANGUAGE=header,
	)

	assert response.status_code == 400
	assert response.json()["currentPassword"] == [esperado]


@pytest.mark.django_db
def test_sin_accept_language_sigue_en_ingles():
	"""El fallback es inglés y no puede cambiar.

	Los APK ya publicados no mandan el header. Si el idioma de respaldo fuera
	español, esas instalaciones pasarían a recibir los errores en un idioma que
	nadie eligió.
	"""
	user = UserFactory(password=PASSWORD)
	client = _auth_client(user)

	response = client.delete(reverse("profile"), {"currentPassword": "no-es-esta"}, format="json")

	assert response.json()["currentPassword"] == ["Current password is incorrect."]


@pytest.mark.django_db
def test_un_mensaje_de_otro_modulo_tambien_se_traduce():
	"""No alcanza con que ande en accounts: el mecanismo es de todo el backend."""
	user = UserFactory(password=PASSWORD)
	client = _auth_client(user)

	response = client.get(
		reverse("restaurant-nearby"), {"lat": "abc", "lng": "2"}, HTTP_ACCEPT_LANGUAGE="it"
	)

	assert response.json()["detail"] == "lat e lng devono essere numerici."


# Un literal suelto dentro de ValidationError(...) o de un {"detail": ...}.
# Busca la comilla de apertura pegada al paréntesis o a la clave: envuelto en
# `_(...)` no matchea, porque en el medio va el `_(`.
SIN_ENVOLVER = re.compile(r'ValidationError\(\s*["\']|["\']detail["\']\s*:\s*["\']')

IGNORADOS = ("tests", "migrations", "__pycache__", "locale", ".venv")


def test_ningun_mensaje_nuevo_queda_sin_envolver():
	"""El check que hace que la regla no dependa de acordarse.

	Los 28 mensajes se envolvieron de una vez; lo que se rompe después es el
	siguiente que alguien agregue. Si este test falla, envolvé el texto en
	`gettext_lazy` (`_("...")`), corré `makemessages -l es -l it` y traducí las
	entradas nuevas en `locale/<lang>/LC_MESSAGES/django.po`.
	"""
	culpables = []
	for archivo in BACKEND.rglob("*.py"):
		if any(parte in IGNORADOS for parte in archivo.parts):
			continue
		for numero, linea in enumerate(archivo.read_text(encoding="utf-8").splitlines(), 1):
			if SIN_ENVOLVER.search(linea):
				culpables.append(f"{archivo.relative_to(BACKEND)}:{numero}: {linea.strip()}")

	assert not culpables, "Mensajes sin gettext:\n" + "\n".join(culpables)
