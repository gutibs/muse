"""El `locationBias` que se le manda a Google no puede pasarse de radio.

Existe porque la búsqueda de ciudad del mapa estuvo devolviendo 502 en
producción: `city_autocomplete` pedía un bias de 500 km y Places API (New)
contesta 400 INVALID_ARGUMENT — "Radius must be between 0 and 50,000 meters" —
así que la búsqueda fallaba **siempre** que el mapa mandara lat/lng, que es
siempre salvo que el query traiga sufijo de país. El mock devuelve lo que
Google devolvería; lo que se afirma acá es el cuerpo del request.
"""

from unittest.mock import patch

import pytest
from rest_framework.test import APIClient

from places.views import MAX_LOCATION_BIAS_RADIUS_M
from tests.factories import UserFactory

CITY_URL = "/api/v1/places/cities/autocomplete/"
RESTAURANT_URL = "/api/v1/places/autocomplete/"

# Google's documented ceiling. Hardcoded a propósito: si alguien sube la
# constante de la app, este test tiene que romper, no acompañarla.
GOOGLE_MAX_RADIUS_M = 50000.0


def _auth_client():
	client = APIClient()
	client.force_authenticate(user=UserFactory())
	return client


@pytest.fixture
def google_autocomplete():
	with (
		patch("places.services.google_places.is_configured", return_value=True),
		patch("places.services.google_places.autocomplete", return_value=[]) as mock,
	):
		yield mock


@pytest.mark.critical
@pytest.mark.django_db
@pytest.mark.parametrize("url", [CITY_URL, RESTAURANT_URL])
def test_location_bias_radius_within_google_limit(url, google_autocomplete):
	"""Ninguna búsqueda con coordenadas puede pedir más de 50 km de bias."""
	res = _auth_client().get(f"{url}?q=London&lat=-34.6&lng=-58.4")

	assert res.status_code == 200
	body = google_autocomplete.call_args.args[0]
	assert body["locationBias"]["circle"]["radius"] <= GOOGLE_MAX_RADIUS_M


@pytest.mark.django_db
def test_location_bias_is_clamped_not_dropped(google_autocomplete):
	"""Un radio excesivo se acota al máximo; no se descarta el bias entero.

	Sin bias, un "london" pelado devuelve London, Ontario — que es el bug que
	el bias existe para evitar."""
	assert MAX_LOCATION_BIAS_RADIUS_M == GOOGLE_MAX_RADIUS_M

	res = _auth_client().get(f"{CITY_URL}?q=London&lat=-34.6&lng=-58.4")

	assert res.status_code == 200
	circle = google_autocomplete.call_args.args[0]["locationBias"]["circle"]
	assert circle["radius"] == GOOGLE_MAX_RADIUS_M
	assert circle["center"] == {"latitude": -34.6, "longitude": -58.4}


@pytest.mark.django_db
def test_country_hint_skips_the_bias(google_autocomplete):
	"""Con país explícito manda el país, no el centro del mapa."""
	res = _auth_client().get(f"{CITY_URL}?q=London UK&lat=-34.6&lng=-58.4")

	assert res.status_code == 200
	body = google_autocomplete.call_args.args[0]
	assert body["includedRegionCodes"] == ["gb"]
	assert body["input"] == "London"
	assert "locationBias" not in body


@pytest.mark.django_db
def test_no_coordinates_means_no_bias(google_autocomplete):
	res = _auth_client().get(f"{CITY_URL}?q=London")

	assert res.status_code == 200
	assert "locationBias" not in google_autocomplete.call_args.args[0]
