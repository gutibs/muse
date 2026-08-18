"""Fotos de Google Places servidas desde nuestro propio storage.

Hasta acá, cada `<img>` de la app pegaba al endpoint de fotos, que resolvía la
URL firmada contra Google en cada carga: una lista de 20 restaurantes eran 20
llamadas facturadas, repetidas en cada scroll. Ahora los bytes se guardan una
vez en el volumen de media —el mismo que ya sirve los avatares, montado
read-only en nginx— y el endpoint redirige ahí.

El TTL de 30 días es el de los Google Maps Platform Terms, igual que el de
`PlaceDetailsCache`. Vencida la ventana la foto se vuelve a bajar y el archivo
viejo se borra: el disco del EC2 ya se llenó una vez y esto crece solo.
"""

from __future__ import annotations

import hashlib
import logging
from datetime import timedelta

from django.core.files.base import ContentFile
from django.utils import timezone

from places.models import PlaceDetailsCache, PlacePhoto
from places.services import google_places

logger = logging.getLogger(__name__)

CACHE_TTL = timedelta(days=30)

# Una foto de Places a 800px ronda los 100-200 KB. El techo está para que una
# respuesta inesperada no llene el disco, no para recortar fotos legítimas.
MAX_PHOTO_BYTES = 5 * 1024 * 1024

# El ancho que pide el cliente de Places. Parte de la clave: si mañana se pide
# otro tamaño, es otro archivo y no debe pisar al existente.
DEFAULT_WIDTH = 800

_EXTENSIONS = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}


def get_or_fetch(
	photo_ref: str,
	*,
	width: int = DEFAULT_WIDTH,
	attributions: list | None = None,
) -> PlacePhoto:
	"""La foto guardada, bajándola de Google si no está o si venció.

	`attributions` sólo lo tiene quien vio el payload de details (el importador):
	el endpoint público recibe únicamente el ref, así que pasa `None` y no pisa
	lo que ya se haya guardado.
	"""
	ref = (photo_ref or "").strip()
	cutoff = timezone.now() - CACHE_TTL

	existing = PlacePhoto.objects.filter(photo_ref=ref, width=width).first()
	if existing and existing.file and existing.fetched_at > cutoff:
		if attributions and existing.attribution != attributions:
			existing.attribution = attributions
			existing.save(update_fields=["attribution"])
		return existing

	# Valida la forma del ref y que la URL resuelta sea de Google. Lanza antes
	# de bajar nada si el ref no tiene la pinta correcta.
	uri = google_places.photo_uri(ref)
	content, content_type = google_places.download_photo(uri, MAX_PHOTO_BYTES)

	extension = _EXTENSIONS.get(content_type)
	if not extension or not content:
		# No es una imagen: guardarlo serviría basura desde nuestro dominio
		# durante 30 días, con nuestra marca puesta.
		logger.warning("Places devolvió %r para la foto %s", content_type, ref)
		raise google_places.GooglePlacesError("Photo response was not an image.")

	# El ref es largo y trae barras; el hash da un nombre estable y plano, así
	# que refrescar una foto sobrescribe en vez de acumular copias.
	digest = hashlib.sha256(f"{ref}@{width}".encode()).hexdigest()
	filename = f"{digest}.{extension}"

	photo = existing or PlacePhoto(photo_ref=ref, width=width)
	if photo.file:
		photo.file.delete(save=False)
	photo.file.save(filename, ContentFile(content), save=False)
	photo.fetched_at = timezone.now()
	if attributions:
		photo.attribution = attributions
	photo.save()
	return photo


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


def attributions_for_ref(photo_ref: str) -> list:
	"""Los `authorAttributions` de esa foto, sacados del details ya cacheado.

	El ref es `places/<place_id>/photos/<id>`, así que el place_id sale de ahí
	y el payload ya está en `PlaceDetailsCache` — la foto nunca se pide antes
	que los detalles del lugar. Evita guardar la atribución en dos lados: es un
	dato de la respuesta de Google, y esa respuesta ya la tenemos.
	"""
	parts = (photo_ref or "").split("/")
	if len(parts) < 2 or parts[0] != "places":
		return []

	cached = PlaceDetailsCache.objects.filter(place_id=parts[1]).order_by("-fetched_at").first()
	if cached is None:
		logger.warning("Sin details cacheado para atribuir la foto %s", photo_ref)
		return []

	for photo in cached.payload.get("photos") or []:
		if photo.get("name") == photo_ref:
			return photo.get("authorAttributions") or []
	return []
