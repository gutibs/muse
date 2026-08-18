"""Caché de fotos de Google Places (places/services/place_photos.py).

Es el volumen grande de la integración: hasta acá, cada `<img>` que pintaba la
app pegaba a la Places Photo API para resolver la URL firmada, así que una
lista de 20 restaurantes eran 20 llamadas facturadas — y se repetían en cada
scroll. Ahora los bytes se guardan en el volumen de media (el mismo que ya
sirve los avatares) y el endpoint redirige ahí.

El TTL de 30 días sale de los Google Maps Platform Terms, igual que el de
`PlaceDetailsCache`.
"""

from datetime import timedelta
from unittest.mock import MagicMock, patch

import pytest
from django.utils import timezone

from places.models import PlacePhoto
from places.services import google_places, place_photos

REF = "places/ChIJN1t_tDeuEmsRUsoyG83frY4/photos/AeJbb3f"
SIGNED_URI = "https://lh3.googleusercontent.com/places/foto-firmada"
JPEG = b"\xff\xd8\xff\xe0" + b"muse" * 32


@pytest.fixture(autouse=True)
def _api_key(settings):
	settings.GOOGLE_PLACES_API_KEY = "test-key"


@pytest.fixture(autouse=True)
def _media_root(settings, tmp_path):
	settings.MEDIA_ROOT = tmp_path / "media"


def _google_serves_photo(content=JPEG, content_type="image/jpeg"):
	"""Mockea las dos llamadas: resolver la URL firmada y bajar los bytes."""
	resolve = MagicMock()
	resolve.json.return_value = {"photoUri": SIGNED_URI}
	resolve.raise_for_status.return_value = None

	download = MagicMock()
	download.iter_content.return_value = [content]
	download.headers = {"Content-Type": content_type, "Content-Length": str(len(content))}
	download.raise_for_status.return_value = None

	def _get(url, *args, **kwargs):
		return download if url == SIGNED_URI else resolve

	return patch("places.services.google_places.requests.get", side_effect=_get)


@pytest.mark.django_db
def test_miss_downloads_the_bytes_and_stores_them():
	with _google_serves_photo() as get:
		photo = place_photos.get_or_fetch(REF)
		assert get.call_count == 2, "Una llamada para resolver la URL y otra para bajarla"

	assert photo.file.read() == JPEG
	assert PlacePhoto.objects.count() == 1


@pytest.mark.django_db
def test_hit_does_not_reach_google():
	with _google_serves_photo() as get:
		first = place_photos.get_or_fetch(REF)
		second = place_photos.get_or_fetch(REF)
		assert get.call_count == 2, "La segunda vez sale del disco, no de Google"

	assert first.pk == second.pk
	assert PlacePhoto.objects.count() == 1


@pytest.mark.django_db
def test_expired_photo_is_refetched_in_place():
	with _google_serves_photo() as get:
		place_photos.get_or_fetch(REF)
		PlacePhoto.objects.filter(photo_ref=REF).update(
			fetched_at=timezone.now() - place_photos.CACHE_TTL - timedelta(minutes=1)
		)
		place_photos.get_or_fetch(REF)
		assert get.call_count == 4

	assert PlacePhoto.objects.count() == 1, "Se refresca la fila, no se agrega otra"


@pytest.mark.django_db
def test_non_image_response_is_rejected_and_not_stored():
	# Si lo que baja no es una imagen, el payload no es lo que creemos:
	# guardarlo serviría basura desde nuestro propio dominio por 30 días.
	with _google_serves_photo(content=b"<html>nope</html>", content_type="text/html"):
		with pytest.raises(google_places.GooglePlacesError):
			place_photos.get_or_fetch(REF)

	assert not PlacePhoto.objects.exists()


@pytest.mark.django_db
def test_oversized_response_is_rejected():
	big = b"x" * (place_photos.MAX_PHOTO_BYTES + 1)
	with _google_serves_photo(content=big):
		with pytest.raises(google_places.GooglePlacesError):
			place_photos.get_or_fetch(REF)

	assert not PlacePhoto.objects.exists()


@pytest.mark.django_db
def test_invalid_ref_never_reaches_google():
	with _google_serves_photo() as get:
		with pytest.raises(google_places.GooglePlacesError):
			place_photos.get_or_fetch("../../etc/passwd")
		assert get.call_count == 0

	assert not PlacePhoto.objects.exists()


@pytest.mark.django_db
def test_attribution_is_recorded_when_the_caller_has_it():
	# Los términos exigen mostrar el autor de la foto. Sólo el payload de
	# details lo trae, así que el importador lo pasa cuando lo tiene.
	attributions = [{"displayName": "Ana P.", "uri": "https://maps.google.com/ana"}]
	with _google_serves_photo():
		photo = place_photos.get_or_fetch(REF, attributions=attributions)

	assert photo.attribution == attributions


@pytest.mark.django_db
def test_purge_expired_only_removes_stale_rows():
	with _google_serves_photo():
		stale = place_photos.get_or_fetch(REF)
		place_photos.get_or_fetch(f"{REF}-otra")

	PlacePhoto.objects.filter(pk=stale.pk).update(
		fetched_at=timezone.now() - place_photos.CACHE_TTL - timedelta(days=1)
	)

	assert place_photos.purge_expired() == 1
	assert PlacePhoto.objects.count() == 1


@pytest.mark.django_db
def test_attribution_comes_from_the_cached_details():
	# La atribución es un dato del payload de details, que ya está cacheado:
	# guardarla también en el Restaurant sería el mismo dato en dos lados.
	from places.models import PlaceDetailsCache

	attributions = [{"displayName": "Ana P.", "uri": "https://maps.google.com/ana"}]
	PlaceDetailsCache.objects.create(
		place_id="ChIJN1t_tDeuEmsRUsoyG83frY4",
		field_mask="id,photos",
		payload={"photos": [{"name": REF, "authorAttributions": attributions}]},
		fetched_at=timezone.now(),
	)

	assert place_photos.attributions_for_ref(REF) == attributions


@pytest.mark.django_db
def test_attribution_lookup_survives_a_ref_with_no_cached_details():
	assert place_photos.attributions_for_ref(REF) == []
	assert place_photos.attributions_for_ref("basura") == []
