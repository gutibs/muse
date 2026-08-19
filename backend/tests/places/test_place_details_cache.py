"""Caché de Place Details (places/services/place_details.py).

Cada llamada a Places Details se factura. El caché existe para no pagar dos
veces por el mismo `place_id`, y vive en Postgres —no en Redis— porque el
deploy hace `down` + `up -d`: una caché en memoria se vacía en cada push y
nunca llega a los 30 días de vida útil que permiten los términos de Google.

El boundary mockeado es `requests.get` del cliente: así un hit se prueba por
lo que NO sale a la red, no por lo que devuelve el service.
"""

from datetime import timedelta
from unittest.mock import MagicMock, patch

import pytest
from django.utils import timezone

from places.models import PlaceDetailsCache
from places.services import google_places, place_details

PLACE_ID = "ChIJN1t_tDeuEmsRUsoyG83frY4"
MASK = "id,displayName,location"
PAYLOAD = {"id": PLACE_ID, "displayName": {"text": "Bar Nacional"}}


@pytest.fixture(autouse=True)
def _api_key(settings):
	settings.GOOGLE_PLACES_API_KEY = "test-key"


def _google_returns(payload=PAYLOAD):
	response = MagicMock()
	response.json.return_value = payload
	response.raise_for_status.return_value = None
	return patch("places.services.google_places.requests.get", return_value=response)


@pytest.mark.django_db
def test_miss_calls_google_and_stores_the_payload():
	with _google_returns() as get:
		assert place_details.get_details(PLACE_ID, MASK) == PAYLOAD
		assert get.call_count == 1

	row = PlaceDetailsCache.objects.get(place_id=PLACE_ID, field_mask=MASK)
	assert row.payload == PAYLOAD


@pytest.mark.django_db
def test_hit_does_not_reach_google():
	with _google_returns() as get:
		place_details.get_details(PLACE_ID, MASK)
		place_details.get_details(PLACE_ID, MASK)
		assert get.call_count == 1, "La segunda lectura tiene que salir del caché"

	assert PlaceDetailsCache.objects.count() == 1


@pytest.mark.django_db
def test_expired_entry_is_refetched_and_updated_in_place():
	with _google_returns() as get:
		place_details.get_details(PLACE_ID, MASK)
		PlaceDetailsCache.objects.filter(place_id=PLACE_ID).update(
			fetched_at=timezone.now() - place_details.CACHE_TTL - timedelta(minutes=1)
		)

		fresh = {"id": PLACE_ID, "displayName": {"text": "Bar Nacional (renombrado)"}}
		get.return_value.json.return_value = fresh

		assert place_details.get_details(PLACE_ID, MASK) == fresh
		assert get.call_count == 2

	assert PlaceDetailsCache.objects.count() == 1, "Se actualiza la fila, no se agrega otra"
	assert PlaceDetailsCache.objects.get(place_id=PLACE_ID).payload == fresh


@pytest.mark.django_db
def test_a_different_field_mask_is_a_different_entry():
	# Si el mask cambia, el payload viejo no tiene los campos nuevos: servirlo
	# daría un restaurante a medio importar y sin forma de notarlo.
	with _google_returns() as get:
		place_details.get_details(PLACE_ID, MASK)
		place_details.get_details(PLACE_ID, f"{MASK},photos")
		assert get.call_count == 2

	assert PlaceDetailsCache.objects.count() == 2


@pytest.mark.django_db
def test_prefixed_place_id_hits_the_same_entry():
	# La API (New) devuelve los ids como 'places/ChIJ...' en algunos payloads;
	# sin normalizar, el mismo lugar se cachearía —y se pagaría— dos veces.
	with _google_returns() as get:
		place_details.get_details(PLACE_ID, MASK)
		place_details.get_details(f"places/{PLACE_ID}", MASK)
		assert get.call_count == 1

	assert PlaceDetailsCache.objects.count() == 1


@pytest.mark.django_db
def test_google_failure_is_not_cached():
	import requests

	with patch(
		"places.services.google_places.requests.get",
		side_effect=requests.RequestException("boom"),
	):
		with pytest.raises(google_places.GooglePlacesError):
			place_details.get_details(PLACE_ID, MASK)

	assert not PlaceDetailsCache.objects.exists(), "Un fallo no se guarda como respuesta"


@pytest.mark.django_db
def test_empty_payload_is_not_cached():
	# Un 200 con cuerpo vacío es una respuesta rota, no un lugar sin datos:
	# guardarla dejaría el place_id envenenado por 30 días.
	with _google_returns(payload={}) as get:
		place_details.get_details(PLACE_ID, MASK)
		place_details.get_details(PLACE_ID, MASK)
		assert get.call_count == 2

	assert not PlaceDetailsCache.objects.exists()


@pytest.mark.django_db
def test_purge_expired_only_removes_stale_rows():
	with _google_returns():
		place_details.get_details(PLACE_ID, MASK)
		place_details.get_details("ChIJfresh0000000000000000000", MASK)

	PlaceDetailsCache.objects.filter(place_id=PLACE_ID).update(
		fetched_at=timezone.now() - place_details.CACHE_TTL - timedelta(days=1)
	)

	assert place_details.purge_expired() == 1
	assert PlaceDetailsCache.objects.count() == 1
	assert not PlaceDetailsCache.objects.filter(place_id=PLACE_ID).exists()
