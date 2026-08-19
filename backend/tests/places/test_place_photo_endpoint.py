"""`/api/v1/places/photo/` — el endpoint público que pintan los `<img>`.

Antes devolvía un 302 a la URL firmada de Google, resuelta con una llamada
facturada en cada carga. Ahora redirige a nuestra copia y sólo sale a Google
la primera vez.
"""

from unittest.mock import MagicMock, patch

import pytest
from rest_framework.test import APIClient

URL = "/api/v1/places/photo/"
REF = "places/ChIJN1t_tDeuEmsRUsoyG83frY4/photos/AeJbb3f"
SIGNED_URI = "https://lh3.googleusercontent.com/places/foto-firmada"
JPEG = b"\xff\xd8\xff\xe0" + b"muse" * 32


@pytest.fixture(autouse=True)
def _api_key(settings):
	settings.GOOGLE_PLACES_API_KEY = "test-key"


@pytest.fixture(autouse=True)
def _media_root(settings, tmp_path):
	settings.MEDIA_ROOT = tmp_path / "media"


def _google_serves_photo():
	resolve = MagicMock()
	resolve.json.return_value = {"photoUri": SIGNED_URI}
	resolve.raise_for_status.return_value = None

	download = MagicMock()
	download.iter_content.return_value = [JPEG]
	download.headers = {"Content-Type": "image/jpeg", "Content-Length": str(len(JPEG))}
	download.raise_for_status.return_value = None

	return patch(
		"places.services.google_places.requests.get",
		side_effect=lambda url, *a, **kw: download if url == SIGNED_URI else resolve,
	)


@pytest.mark.django_db
def test_photo_redirects_to_our_own_media_and_is_cacheable():
	client = APIClient()
	with _google_serves_photo():
		res = client.get(URL, {"ref": REF})

	assert res.status_code == 302
	assert res["Location"].startswith("/media/place-photos/")
	assert "max-age" in res["Cache-Control"]


@pytest.mark.django_db
def test_second_request_does_not_reach_google():
	client = APIClient()
	with _google_serves_photo() as get:
		client.get(URL, {"ref": REF})
		calls_after_first = get.call_count
		res = client.get(URL, {"ref": REF})

	assert res.status_code == 302
	assert get.call_count == calls_after_first, "El segundo request sale del disco"


@pytest.mark.django_db
def test_photo_endpoint_stays_public():
	# Los <img> no mandan Authorization: si esto pide auth, la app no muestra
	# ninguna foto.
	client = APIClient()
	with _google_serves_photo():
		res = client.get(URL, {"ref": REF})

	assert res.status_code != 401


@pytest.mark.django_db
def test_invalid_ref_is_rejected():
	res = APIClient().get(URL, {"ref": "../../etc/passwd"})
	assert res.status_code == 400


@pytest.mark.django_db
def test_cached_photo_is_served_even_without_the_api_key(settings):
	"""Una foto ya guardada no necesita a Google para servirse.

	Encontrado probando en vivo: la view chequeaba `is_configured()` antes de
	mirar el caché, así que con la key ausente —o rotada, o con la cuota
	agotada— devolvía 503 aunque el archivo estuviera en disco. En producción
	eso es quedarse sin ninguna foto por un problema que ya no nos afecta.
	"""
	client = APIClient()
	with _google_serves_photo():
		client.get(URL, {"ref": REF})

	settings.GOOGLE_PLACES_API_KEY = ""
	res = client.get(URL, {"ref": REF})

	assert res.status_code == 302
	assert res["Location"].startswith("/media/place-photos/")


@pytest.mark.django_db
def test_uncached_photo_without_the_api_key_still_fails_cleanly(settings):
	settings.GOOGLE_PLACES_API_KEY = ""
	res = APIClient().get(URL, {"ref": REF})
	assert res.status_code == 503
