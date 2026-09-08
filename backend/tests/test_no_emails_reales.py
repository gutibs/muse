"""Ningún test puede mandar un email de verdad.

Hasta el 2026-09-08 sí podían, y lo hacían: cada alta en la suite llamaba a la
API de Resend por la red. Sólo no llegaba un mail porque Resend rechaza
`@example.com` con "Please use our testing email address", y porque
`RegisterSerializer._notify` se traga el `EmailSendError` — o sea que el fallo
ni siquiera se veía. Con un dominio válido en un test, la suite le manda un
correo a una persona real.

Aparte del correo indeseado: la suite dependía de la red y del cupo de una
cuenta paga para pasar.

El fixture que lo impide es `_sin_emails_reales`, en `conftest.py`. Este archivo
existe para que nadie lo saque sin enterarse.
"""

from unittest.mock import Mock

import pytest
import resend
from django.urls import reverse
from rest_framework.test import APIClient


def test_resend_esta_parcheado_en_toda_la_suite():
	"""El chequeo directo: si esto es la función real, algo va a salir a la red."""
	assert isinstance(
		resend.Emails.send, Mock
	), "resend.Emails.send no está mockeado: un test puede mandar un email real"


@pytest.mark.django_db
def test_un_alta_no_sale_a_la_red(emails_enviados, settings):
	"""El camino por el que se colaba: `RegisterView` manda el mail de bienvenida.

	La key se fija acá a propósito. Sin ella `_ensure_configured` corta antes de
	llegar a Resend y `_notify` se come el `EmailSendError`, así que el test
	pasaría sin probar nada — y pasaría **sólo donde hay key**: en local, por el
	`.env`, y no en CI. Eso es exactamente lo que rompió el build.
	"""
	settings.RESEND_API_KEY = "re_test_key"
	client = APIClient()

	response = client.post(
		reverse("register"),
		{
			"email": "nueva@example.com",
			"password": "Sup3r-strong-pass!",
			"displayName": "Nueva",
			"acceptPrivacy": True,
		},
		format="json",
	)

	# 202 y no 201: el alta no revela si el email ya existía (test_register_no_oracle).
	assert response.status_code == 202, response.content
	# El mail se mandó, pero contra el mock: la prueba de que el camino existe
	# y de que ya no toca la red.
	emails_enviados.assert_called_once()
	assert emails_enviados.call_args[0][0]["to"] == ["nueva@example.com"]
