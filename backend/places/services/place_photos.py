"""Fotos de Google Places servidas desde nuestro propio storage.

Se resuelven por `place_id`. El nombre de recurso de la foto —el "photo ref"—
**caduca**: los que estaban guardados desde el import devolvían
`400 INVALID_ARGUMENT: The photo resource in the request is invalid` mientras un
details fresco del mismo lugar daba otro ref que sí servía (verificado contra la
API el 2026-08-19). Guardar el ref, entonces, es guardar un puntero que se
vuelve inválido solo.

El place_id no caduca y el details ya está cacheado 30 días, así que el ref se
pide en el momento, se usa, y se descarta. Una vez que los bytes están en el
volumen de media —el mismo que sirve los avatares, montado read-only en nginx—
la caducidad deja de importar: la foto se sirve sin hablar con Google.
"""

from __future__ import annotations

import hashlib
import logging
from datetime import timedelta

from django.core.files.base import ContentFile
from django.utils import timezone

from places.models import PlaceDetailsCache, PlacePhoto
from places.services import google_places, place_details

logger = logging.getLogger(__name__)

CACHE_TTL = timedelta(days=30)

# Una foto de Places a 800px ronda los 100-200 KB. El techo está para que una
# respuesta inesperada no llene el disco, no para recortar fotos legítimas.
MAX_PHOTO_BYTES = 5 * 1024 * 1024

# El ancho que se le pide a Google. Parte de la clave: si mañana se pide otro
# tamaño, es otro archivo y no debe pisar al existente.
DEFAULT_WIDTH = 800

_EXTENSIONS = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}


def place_id_from_ref(photo_ref: str) -> str:
	"""El place_id embebido en un photo ref (`places/<place_id>/photos/<id>`).

	Existe para los clientes que todavía piden fotos por ref: el ref puede estar
	vencido, pero el place_id que lleva adentro sigue siendo bueno.
	"""
	parts = (photo_ref or "").split("/")
	if len(parts) < 2 or parts[0] != "places":
		return ""
	return parts[1]


def _current_photo_ref(place_id: str) -> str:
	"""El ref vigente de la primera foto del lugar, según el details cacheado."""
	# Import local: el mask vive con el parser, y así no se acopla el arranque
	# de este módulo al de la app de restaurants.
	from restaurants.services.google_place_parser import FIELD_MASK

	payload = place_details.get_details(place_id, FIELD_MASK)
	photos = payload.get("photos") or []
	if not photos:
		raise google_places.GooglePlacesError("Place has no photos.", status_code=404)
	return photos[0].get("name") or ""


def get_or_fetch(place_id: str, *, width: int = DEFAULT_WIDTH) -> PlacePhoto:
	"""La foto guardada del lugar, bajándola de Google si no está o si venció."""
	bare_id = google_places.validated_place_id(place_id)

	existing = PlacePhoto.objects.filter(place_id=bare_id, width=width).first()
	if existing and existing.file and existing.fetched_at > timezone.now() - CACHE_TTL:
		return existing

	# Siempre se vuelve a preguntar cuál es el ref vigente: el que quedó
	# guardado en `existing.photo_ref` es justamente el que puede haber vencido.
	ref = _current_photo_ref(bare_id)
	uri = google_places.photo_uri(ref)
	content, content_type = google_places.download_photo(uri, MAX_PHOTO_BYTES)

	extension = _EXTENSIONS.get(content_type)
	if not extension or not content:
		# No es una imagen: guardarlo serviría basura desde nuestro dominio
		# durante 30 días, con nuestra marca puesta.
		logger.warning("Places devolvió %r para la foto de %s", content_type, bare_id)
		raise google_places.GooglePlacesError("Photo response was not an image.")

	# Nombre estable y plano derivado de la clave, así que refrescar una foto
	# sobrescribe en vez de acumular copias en el disco.
	digest = hashlib.sha256(f"{bare_id}@{width}".encode()).hexdigest()
	filename = f"{digest}.{extension}"

	photo = existing or PlacePhoto(place_id=bare_id, width=width)
	if photo.file:
		photo.file.delete(save=False)
	photo.file.save(filename, ContentFile(content), save=False)
	photo.photo_ref = ref
	photo.fetched_at = timezone.now()
	photo.attribution = attributions_for_place(bare_id)
	photo.save()
	return photo


def attributions_for_place(place_id: str) -> list:
	"""Los `authorAttributions` de la foto, del details ya cacheado.

	No se guardan en el Restaurant: son parte de la respuesta de Google, y esa
	respuesta ya la tenemos guardada.
	"""
	bare_id = google_places.normalize_place_id((place_id or "").strip())
	if not bare_id:
		return []

	cached = PlaceDetailsCache.objects.filter(place_id=bare_id).order_by("-fetched_at").first()
	if cached is None:
		logger.warning("Sin details cacheado para atribuir la foto de %s", bare_id)
		return []

	photos = cached.payload.get("photos") or []
	return (photos[0].get("authorAttributions") or []) if photos else []


def purge_expired() -> int:
	"""Borra las fotos fuera de la ventana de 30 días, con sus archivos."""
	stale = PlacePhoto.objects.filter(fetched_at__lte=timezone.now() - CACHE_TTL)
	deleted = 0
	for photo in stale:
		# `queryset.delete()` no toca el storage: sin esto las filas se van y
		# los archivos quedan ocupando el disco para siempre.
		photo.file.delete(save=False)
		photo.delete()
		deleted += 1
	return deleted
