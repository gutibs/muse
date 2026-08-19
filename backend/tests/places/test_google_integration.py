"""Tests contra la API de Google de verdad. No mockean nada.

Existen por lo que pasó el 2026-08-19: la suite entera estaba en verde y las
fotos no funcionaban en producción, porque los mocks devolvían exactamente lo
que el código esperaba. Google no. Los photo refs guardados habían caducado y
la API contestaba `400 INVALID_ARGUMENT`, algo que ningún test con
`requests.get` mockeado puede descubrir.

Se saltean solos cuando no hay `GOOGLE_PLACES_API_KEY`, así que CI sigue verde
sin credenciales y estos corren cuando alguien tiene una key de dev:

    docker compose -f docker-compose.dev.yml run --rm backend pytest -m integration

Cada corrida gasta cuota facturada. Son pocos y a propósito.
"""

import pytest
from django.conf import settings

from places.models import PlacePhoto
from places.services import google_places, place_details, place_photos
from restaurants.services.google_place_parser import FIELD_MASK, parse_place

pytestmark = pytest.mark.integration

# El place de la documentación de Google. Estable y público: si un día deja de
# existir, que el test lo diga en vez de arrastrar un id inventado.
PLACE_ID = "ChIJN1t_tDeuEmsRUsoyG83frY4"


@pytest.fixture(autouse=True)
def _requiere_key():
	if not settings.GOOGLE_PLACES_API_KEY:
		pytest.skip("Sin GOOGLE_PLACES_API_KEY: estos tests hablan con Google de verdad.")


@pytest.fixture(autouse=True)
def _media_root(settings, tmp_path):
	settings.MEDIA_ROOT = tmp_path / "media"


@pytest.mark.django_db
def test_details_trae_los_campos_que_el_parser_espera():
	"""El contrato real de la API, no el que asumen los mocks."""
	payload = place_details.get_details(PLACE_ID, FIELD_MASK)
	parsed = parse_place(payload)

	assert parsed["place_id"] == PLACE_ID
	assert parsed["name"], "displayName.text vacío: cambió la forma de la respuesta"
	assert parsed["lat"] is not None and parsed["lng"] is not None


@pytest.mark.django_db
def test_details_trae_la_atribucion_que_exigen_los_terminos():
	# Los Google Maps Platform Terms obligan a mostrar el autor junto a la foto.
	# Si el field mask dejara de pedir `photos` completo, esto se vacía y la
	# obligación se incumple en silencio.
	payload = place_details.get_details(PLACE_ID, FIELD_MASK)
	fotos = payload.get("photos") or []

	assert fotos, "El place no devolvió fotos"
	assert fotos[0].get("authorAttributions"), "Sin authorAttributions en el payload"


@pytest.mark.django_db
def test_la_foto_se_baja_y_queda_guardada():
	"""El flujo completo: details -> ref vigente -> bytes -> disco."""
	foto = place_photos.get_or_fetch(PLACE_ID)

	assert foto.file.size > 1000, "Una foto de Places pesa bastante más que esto"
	assert foto.file.read(2) == b"\xff\xd8", "No es un JPEG"
	assert foto.attribution, "Se guardó sin atribución"
	assert PlacePhoto.objects.count() == 1


@pytest.mark.django_db
def test_un_photo_ref_viejo_ya_no_sirve_pero_el_place_id_si():
	"""La regresión que costó un deploy a producción para descubrirse.

	Un ref con forma válida que Google ya no reconoce da 400. Es exactamente lo
	que pasaba con los refs guardados en `image_url` desde el import: por eso la
	foto se resuelve por place_id y el ref se pide en el momento.
	"""
	ref_invalido = f"places/{PLACE_ID}/photos/AeJbb3fRefQueGoogleNoConoce0000"

	with pytest.raises(google_places.GooglePlacesError):
		google_places.photo_uri(ref_invalido)

	# El mismo lugar, resuelto como corresponde, sí funciona.
	assert place_photos.get_or_fetch(PLACE_ID).file.size > 1000
