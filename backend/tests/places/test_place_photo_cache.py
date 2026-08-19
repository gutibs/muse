"""Caché de fotos de Google Places (places/services/place_photos.py).

La foto se resuelve por `place_id`, no por el nombre de recurso de la foto.
Razón, verificada contra la API real el 2026-08-19: los photo refs caducan.
Los que estaban guardados desde el import devolvían
`400 INVALID_ARGUMENT: The photo resource in the request is invalid`, mientras
que un details fresco del mismo lugar daba un ref distinto que sí funcionaba.

El place_id no caduca, y el details ya está cacheado 30 días, así que el ref
pasa a ser un detalle interno y efímero: se pide en el momento, se usan los
bytes, y una vez guardados la caducidad deja de importar.
"""

from datetime import timedelta
from unittest.mock import MagicMock, patch

import pytest
from django.utils import timezone

from places.models import PlaceDetailsCache, PlacePhoto
from places.services import google_places, place_photos
from restaurants.services.google_place_parser import FIELD_MASK

PLACE_ID = "ChIJN1t_tDeuEmsRUsoyG83frY4"
REF = f"places/{PLACE_ID}/photos/AeJbb3f-vigente"
REF_VIEJO = f"places/{PLACE_ID}/photos/AeJbb3f-vencido"
SIGNED_URI = "https://lh3.googleusercontent.com/places/foto-firmada"
JPEG = b"\xff\xd8\xff\xe0" + b"muse" * 32
ATTRIBUTIONS = [{"displayName": "Ana P.", "uri": "https://maps.google.com/ana"}]


@pytest.fixture(autouse=True)
def _api_key(settings):
	settings.GOOGLE_PLACES_API_KEY = "test-key"


@pytest.fixture(autouse=True)
def _media_root(settings, tmp_path):
	settings.MEDIA_ROOT = tmp_path / "media"


def _cache_details(ref=REF, attributions=ATTRIBUTIONS):
	"""El details cacheado, que es de donde sale el ref vigente."""
	return PlaceDetailsCache.objects.create(
		place_id=PLACE_ID,
		field_mask=FIELD_MASK,
		payload={"photos": [{"name": ref, "authorAttributions": attributions}]},
		fetched_at=timezone.now(),
	)


def _google_serves(content=JPEG, content_type="image/jpeg", details_ref=REF):
	"""Mockea las tres llamadas posibles: details, resolver la URL y bajar bytes."""
	details = MagicMock()
	details.json.return_value = {
		"id": PLACE_ID,
		"photos": [{"name": details_ref, "authorAttributions": ATTRIBUTIONS}],
	}
	details.raise_for_status.return_value = None

	resolve = MagicMock()
	resolve.json.return_value = {"photoUri": SIGNED_URI}
	resolve.raise_for_status.return_value = None

	download = MagicMock()
	download.iter_content.return_value = [content]
	download.headers = {"Content-Type": content_type, "Content-Length": str(len(content))}
	download.raise_for_status.return_value = None

	def _get(url, *args, **kwargs):
		if url == SIGNED_URI:
			return download
		if "/media" in url:
			return resolve
		return details

	return patch("places.services.google_places.requests.get", side_effect=_get)


@pytest.mark.django_db
def test_miss_resolves_the_ref_from_the_cached_details_and_stores_the_bytes():
	_cache_details()
	with _google_serves() as get:
		photo = place_photos.get_or_fetch(PLACE_ID)
		# Sólo resolver la URL firmada y bajarla: el ref salió del caché.
		assert get.call_count == 2

	assert photo.file.read() == JPEG
	assert photo.place_id == PLACE_ID
	assert photo.photo_ref == REF, "Guarda con qué ref se bajó, para poder diagnosticar"
	assert photo.attribution == ATTRIBUTIONS


@pytest.mark.django_db
def test_hit_does_not_reach_google():
	_cache_details()
	with _google_serves() as get:
		first = place_photos.get_or_fetch(PLACE_ID)
		calls = get.call_count
		second = place_photos.get_or_fetch(PLACE_ID)
		assert get.call_count == calls, "La segunda vez sale del disco"

	assert first.pk == second.pk
	assert PlacePhoto.objects.count() == 1


@pytest.mark.django_db
def test_a_stale_stored_ref_does_not_break_anything():
	"""El caso que rompió producción: el ref viejo ya no sirve.

	La foto guardada trae el ref con el que se bajó, pero al refrescarla se
	vuelve a preguntar cuál es el ref vigente en vez de reusar aquél.
	"""
	_cache_details(ref=REF)
	with _google_serves() as get:
		photo = place_photos.get_or_fetch(PLACE_ID)
		PlacePhoto.objects.filter(pk=photo.pk).update(
			photo_ref=REF_VIEJO,
			fetched_at=timezone.now() - place_photos.CACHE_TTL - timedelta(minutes=1),
		)
		refreshed = place_photos.get_or_fetch(PLACE_ID)
		assert get.call_count == 4

	assert refreshed.photo_ref == REF, "Usa el ref vigente, no el que tenía guardado"
	assert PlacePhoto.objects.count() == 1, "Refresca la fila, no agrega otra"


@pytest.mark.django_db
def test_details_is_fetched_when_it_is_not_cached_yet():
	# Sin details en caché hay que pedirlo: tres llamadas en total, y la de
	# details queda cacheada para las próximas.
	with _google_serves() as get:
		photo = place_photos.get_or_fetch(PLACE_ID)
		assert get.call_count == 3

	assert photo.photo_ref == REF
	assert PlaceDetailsCache.objects.filter(place_id=PLACE_ID).exists()


@pytest.mark.django_db
def test_place_without_photos_raises_instead_of_storing_nothing():
	PlaceDetailsCache.objects.create(
		place_id=PLACE_ID,
		field_mask=FIELD_MASK,
		payload={"id": PLACE_ID},
		fetched_at=timezone.now(),
	)
	with pytest.raises(google_places.GooglePlacesError):
		place_photos.get_or_fetch(PLACE_ID)

	assert not PlacePhoto.objects.exists()


@pytest.mark.django_db
def test_non_image_response_is_rejected_and_not_stored():
	_cache_details()
	with _google_serves(content=b"<html>nope</html>", content_type="text/html"):
		with pytest.raises(google_places.GooglePlacesError):
			place_photos.get_or_fetch(PLACE_ID)

	assert not PlacePhoto.objects.exists()


@pytest.mark.django_db
def test_oversized_response_is_rejected():
	_cache_details()
	with _google_serves(content=b"x" * (place_photos.MAX_PHOTO_BYTES + 1)):
		with pytest.raises(google_places.GooglePlacesError):
			place_photos.get_or_fetch(PLACE_ID)

	assert not PlacePhoto.objects.exists()


@pytest.mark.django_db
def test_invalid_place_id_never_reaches_google():
	with _google_serves() as get:
		with pytest.raises(google_places.GooglePlacesError):
			place_photos.get_or_fetch("../../etc/passwd")
		assert get.call_count == 0

	assert not PlacePhoto.objects.exists()


@pytest.mark.django_db
def test_attributions_come_from_the_cached_details():
	_cache_details()
	assert place_photos.attributions_for_place(PLACE_ID) == ATTRIBUTIONS
	assert place_photos.attributions_for_place("ChIJsinDetails") == []
	assert place_photos.attributions_for_place("") == []


@pytest.mark.django_db
def test_purge_expired_only_removes_stale_rows():
	_cache_details()
	with _google_serves():
		stale = place_photos.get_or_fetch(PLACE_ID)
	PlacePhoto.objects.filter(pk=stale.pk).update(
		fetched_at=timezone.now() - place_photos.CACHE_TTL - timedelta(days=1)
	)
	PlacePhoto.objects.create(
		place_id="ChIJotroLugar",
		width=800,
		photo_ref="places/ChIJotroLugar/photos/x",
		file="place-photos/otro.jpg",
		fetched_at=timezone.now(),
	)

	assert place_photos.purge_expired() == 1
	assert PlacePhoto.objects.count() == 1


@pytest.mark.django_db
def test_a_row_whose_file_is_missing_is_refetched():
	"""Una fila sin bytes en disco no es un hit.

	Aparece al restaurar un dump de producción en local: las filas vienen en el
	backup, los archivos viven en el volumen del servidor. `bool(photo.file)`
	es verdadero igual, así que el endpoint devolvía un 302 a un 404 y encima
	sin salir a Google, o sea sin forma de recuperarse hasta que venciera el
	TTL de 30 días.
	"""
	_cache_details()
	with _google_serves() as get:
		photo = place_photos.get_or_fetch(PLACE_ID)
		photo.file.storage.delete(photo.file.name)
		calls = get.call_count

		recuperada = place_photos.get_or_fetch(PLACE_ID)
		assert get.call_count > calls, "Tiene que volver a bajarla"

	assert recuperada.file.storage.exists(recuperada.file.name)
	assert PlacePhoto.objects.count() == 1


@pytest.mark.django_db
def test_purge_orphan_files_removes_files_without_a_row():
	"""Los archivos sin fila no se reusan nunca y hacen crecer el disco.

	Django no sobrescribe: si el archivo existe, la próxima descarga escribe una
	copia con sufijo al lado. Un huérfano de 180 KB se vuelve 360.
	"""
	from django.core.files.base import ContentFile
	from django.core.files.storage import default_storage

	_cache_details()
	with _google_serves():
		viva = place_photos.get_or_fetch(PLACE_ID)

	huerfano = default_storage.save(f"{place_photos.PHOTO_DIR}/sobrante.jpg", ContentFile(JPEG))
	# El guard de edad: recién escrito, todavía no se toca.
	assert place_photos.purge_orphan_files() == 0

	viejo = timezone.now() - place_photos.ORPHAN_MIN_AGE - timedelta(hours=1)
	with patch("django.core.files.storage.FileSystemStorage.get_modified_time", return_value=viejo):
		assert place_photos.purge_orphan_files() == 1

	assert not default_storage.exists(huerfano)
	assert default_storage.exists(viva.file.name), "La foto con fila no se toca"
