"""Lectura cacheada de Google Places Details.

Envuelve a `google_places.details`, que sigue siendo un cliente HTTP puro:
no conoce el ORM ni sabe que existe una caché. Los dos únicos call sites
—`restaurants/services/google_import.py` y `places/views.py`— entran por acá.
"""

from __future__ import annotations

import logging
from datetime import timedelta

from django.utils import timezone

from places.models import PlaceDetailsCache
from places.services import google_places

logger = logging.getLogger(__name__)

# Máximo que los Google Maps Platform Terms permiten conservar el contenido
# de un Place. No subirlo sin leerlos: no es un número de performance.
CACHE_TTL = timedelta(days=30)


def get_details(place_id: str, field_mask: str) -> dict:
	"""El payload de Places Details, del caché si está fresco.

	Propaga `GooglePlacesError` igual que el cliente: un fallo no se guarda,
	así el siguiente intento vuelve a salir a Google en lugar de arrastrar el
	error por 30 días.
	"""
	bare_id = google_places.normalize_place_id((place_id or "").strip())

	cached = PlaceDetailsCache.objects.filter(
		place_id=bare_id,
		field_mask=field_mask,
		fetched_at__gt=timezone.now() - CACHE_TTL,
	).first()
	if cached is not None:
		return cached.payload

	payload = google_places.details(bare_id, field_mask)

	if not payload:
		# Un 200 con cuerpo vacío es una respuesta rota, no un lugar sin datos.
		# Guardarla dejaría el place_id envenenado hasta que venza el TTL.
		logger.warning("Places details devolvió un payload vacío para %s", bare_id)
		return payload

	PlaceDetailsCache.objects.update_or_create(
		place_id=bare_id,
		field_mask=field_mask,
		defaults={"payload": payload, "fetched_at": timezone.now()},
	)
	return payload


def purge_expired() -> int:
	"""Borra las entradas fuera de la ventana de 30 días. Devuelve cuántas."""
	deleted, _ = PlaceDetailsCache.objects.filter(
		fetched_at__lte=timezone.now() - CACHE_TTL
	).delete()
	return deleted
