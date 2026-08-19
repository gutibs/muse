"""`/api/v1/places/photo/` — el endpoint público que pintan los `<img>`.

Antes resolvía la URL firmada contra Google en cada carga y redirigía ahí.
Ahora redirige a nuestra copia y sólo sale a Google la primera vez.

Recibe `place` (place_id). El `ref` sigue aceptándose porque el place_id viaja
adentro del ref: un cliente con una URL vieja tiene que seguir viendo la foto,
aunque ese ref ya esté vencido del lado de Google.
"""

from unittest.mock import MagicMock, patch

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from places.models import PlaceDetailsCache, PlacePhoto
from restaurants.services.google_place_parser import FIELD_MASK

URL = "/api/v1/places/photo/"
PLACE_ID = "ChIJN1t_tDeuEmsRUsoyG83frY4"
REF = f"places/{PLACE_ID}/photos/AeJbb3f-vigente"
REF_VENCIDO = f"places/{PLACE_ID}/photos/AeJbb3f-vencido"
SIGNED_URI = "https://lh3.googleusercontent.com/places/foto-firmada"
JPEG = b"\xff\xd8\xff\xe0" + b"muse" * 32
ATTRIBUTIONS = [{"displayName": "Ana P.", "uri": "https://maps.google.com/ana"}]


@pytest.fixture(autouse=True)
def _api_key(settings):
	settings.GOOGLE_PLACES_API_KEY = "test-key"


@pytest.fixture(autouse=True)
def _media_root(settings, tmp_path):
	settings.MEDIA_ROOT = tmp_path / "media"


def _cache_details():
	PlaceDetailsCache.objects.create(
		place_id=PLACE_ID,
		field_mask=FIELD_MASK,
		payload={"photos": [{"name": REF, "authorAttributions": ATTRIBUTIONS}]},
		fetched_at=timezone.now(),
	)


def _google_serves_photo():
	details = MagicMock()
	details.json.return_value = {"id": PLACE_ID, "photos": [{"name": REF}]}
	details.raise_for_status.return_value = None

	resolve = MagicMock()
	resolve.json.return_value = {"photoUri": SIGNED_URI}
	resolve.raise_for_status.return_value = None

	download = MagicMock()
	download.iter_content.return_value = [JPEG]
	download.headers = {"Content-Type": "image/jpeg", "Content-Length": str(len(JPEG))}
	download.raise_for_status.return_value = None

	def _get(url, *args, **kwargs):
		if url == SIGNED_URI:
			return download
		return resolve if "/media" in url else details

	return patch("places.services.google_places.requests.get", side_effect=_get)


@pytest.mark.django_db
def test_photo_redirects_to_our_own_media_and_is_cacheable():
	_cache_details()
	with _google_serves_photo():
		res = APIClient().get(URL, {"place": PLACE_ID})

	assert res.status_code == 302
	assert res["Location"].startswith("/media/place-photos/")
	assert "max-age" in res["Cache-Control"]


@pytest.mark.django_db
def test_second_request_does_not_reach_google():
	_cache_details()
	client = APIClient()
	with _google_serves_photo() as get:
		client.get(URL, {"place": PLACE_ID})
		calls = get.call_count
		res = client.get(URL, {"place": PLACE_ID})

	assert res.status_code == 302
	assert get.call_count == calls, "El segundo request sale del disco"


@pytest.mark.django_db
def test_a_stale_ref_in_the_url_still_serves_the_photo():
	"""El caso que rompió producción, visto desde el cliente.

	Una URL vieja trae un ref que Google ya rechaza. El place_id que lleva
	adentro alcanza para resolver el ref vigente y servir la foto.
	"""
	_cache_details()
	with _google_serves_photo():
		res = APIClient().get(URL, {"ref": REF_VENCIDO})

	assert res.status_code == 302
	assert res["Location"].startswith("/media/place-photos/")
	assert PlacePhoto.objects.get(place_id=PLACE_ID).photo_ref == REF


@pytest.mark.django_db
def test_photo_endpoint_stays_public():
	# Los <img> no mandan Authorization: si esto pide auth, la app no muestra
	# ninguna foto.
	_cache_details()
	with _google_serves_photo():
		res = APIClient().get(URL, {"place": PLACE_ID})

	assert res.status_code != 401


@pytest.mark.django_db
def test_invalid_place_is_rejected():
	res = APIClient().get(URL, {"place": "../../etc/passwd"})
	assert res.status_code == 400


@pytest.mark.django_db
def test_cached_photo_is_served_even_without_the_api_key(settings):
	"""Una foto ya guardada no necesita a Google para servirse.

	Encontrado probando en vivo: la view chequeaba `is_configured()` antes de
	mirar el caché, así que con la key ausente —o rotada, o con la cuota
	agotada— devolvía 503 aunque el archivo estuviera en disco.
	"""
	_cache_details()
	client = APIClient()
	with _google_serves_photo():
		client.get(URL, {"place": PLACE_ID})

	settings.GOOGLE_PLACES_API_KEY = ""
	res = client.get(URL, {"place": PLACE_ID})

	assert res.status_code == 302
	assert res["Location"].startswith("/media/place-photos/")


@pytest.mark.django_db
def test_uncached_photo_without_the_api_key_still_fails_cleanly(settings):
	settings.GOOGLE_PLACES_API_KEY = ""
	res = APIClient().get(URL, {"place": PLACE_ID})
	assert res.status_code == 503
