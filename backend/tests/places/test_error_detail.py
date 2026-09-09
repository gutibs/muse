"""Qué queda registrado cuando Google rechaza una llamada.

`raise_for_status` guarda el código y tira el cuerpo, y el código solo no
alcanza: Google contesta 403 tanto para una key restringida a otra IP como
para un proyecto sin billing. El 2026-09-08 fue lo segundo y el diagnóstico
salió a mano, con `gcloud`, porque el log no lo distinguía.

Estos tests cubren que el motivo llegue legible: lo lee una persona en un mail,
no un parser.
"""

from unittest.mock import Mock

import requests

from places.services.google_places import _error_detail


def _http_error(*, status, json_body=None, text=""):
	response = Mock(spec=["status_code", "text", "json"])
	response.status_code = status
	response.text = text
	if json_body is None:
		response.json.side_effect = ValueError("no es JSON")
	else:
		response.json.return_value = json_body
	return requests.HTTPError(f"{status} Client Error", response=response)


def test_el_error_de_google_sale_en_una_linea():
	exc = _http_error(
		status=403,
		json_body={
			"error": {
				"code": 403,
				"status": "PERMISSION_DENIED",
				"message": "Places API has not been used in project 123 before or it is disabled.",
			}
		},
	)

	detail = _error_detail(exc)

	assert detail.startswith("HTTP 403: PERMISSION_DENIED")
	assert "disabled" in detail
	# Sin el JSON crudo alrededor: el mail lo lee una persona.
	assert "{" not in detail


def test_una_respuesta_que_no_es_json_se_recorta_igual():
	exc = _http_error(status=502, text="<html><body>Bad gateway</body></html>")

	detail = _error_detail(exc)

	assert detail == "HTTP 502: <html><body>Bad gateway</body></html>"


def test_un_cuerpo_enorme_no_se_lleva_el_mail_puesto():
	exc = _http_error(status=500, text="x" * 5000)

	assert len(_error_detail(exc)) < 600


def test_sin_respuesta_queda_el_tipo_de_fallo():
	"""Un timeout no trae respuesta: el nombre de la excepción es todo lo que hay."""
	detail = _error_detail(requests.ConnectTimeout("connection timed out"))

	assert "ConnectTimeout" in detail
	assert "timed out" in detail


def test_un_error_que_es_texto_y_no_objeto_no_revienta():
	"""Varios frontends de GCP contestan con la forma OAuth: `error` es un string.

	Llamar `.get()` sobre eso lanza `AttributeError` **dentro** del `except
	requests.RequestException` de quien llama, así que no lo atrapa nadie: la
	view devuelve 500 en vez de 502, y el chequeo de salud aborta antes de
	registrar el corte que existe para avisar.
	"""
	exc = _http_error(status=403, json_body={"error": "PERMISSION_DENIED"})

	detail = _error_detail(exc)

	assert detail == "HTTP 403: PERMISSION_DENIED"
