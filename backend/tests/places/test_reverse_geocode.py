"""ReverseGeocodeView (places/views.py) — proxy to Nominatim.

Replaces a direct browser-side hit that violated Nominatim's usage policy
(no User-Agent, no rate limit, no contact email). The view requires auth,
validates coords, and forwards a minimal response shape.
"""

from unittest.mock import MagicMock, patch

import pytest
from rest_framework.test import APIClient

from tests.factories import UserFactory

URL = "/api/v1/places/reverse-geocode/"


@pytest.mark.critical
@pytest.mark.django_db
def test_reverse_geocode_unauthenticated():
	client = APIClient()
	res = client.get(f"{URL}?lat=0&lng=0")
	assert res.status_code == 401


@pytest.mark.critical
@pytest.mark.django_db
def test_reverse_geocode_invalid_coords():
	client = APIClient()
	client.force_authenticate(user=UserFactory())
	res = client.get(f"{URL}?lat=foo&lng=bar")
	assert res.status_code == 400


@pytest.mark.critical
@pytest.mark.django_db
def test_reverse_geocode_out_of_range():
	client = APIClient()
	client.force_authenticate(user=UserFactory())
	res = client.get(f"{URL}?lat=100&lng=0")
	assert res.status_code == 400


@pytest.mark.critical
@pytest.mark.django_db
def test_reverse_geocode_success():
	client = APIClient()
	client.force_authenticate(user=UserFactory())

	mock_resp = MagicMock()
	mock_resp.raise_for_status = MagicMock()
	mock_resp.json.return_value = {
		"display_name": "Av. Corrientes 1234, Buenos Aires, Argentina",
		"address": {
			"road": "Av. Corrientes",
			"house_number": "1234",
			"city": "Buenos Aires",
			"country": "Argentina",
		},
	}

	with patch("places.views.requests.get", return_value=mock_resp) as mock_get:
		res = client.get(f"{URL}?lat=-34.6&lng=-58.4")

	assert res.status_code == 200
	# res.data is pre-render (snake_case), res.json() is post-render
	# (camelCase via djangorestframework-camel-case). Test the wire shape.
	body = res.json()
	assert "Buenos Aires" in body["displayName"]
	addr = body["address"]
	assert addr["city"] == "Buenos Aires"
	assert addr["country"] == "Argentina"
	# House number / road keys keep their snake_case form because they're
	# inside a nested dict and the renderer doesn't recurse into 'address'
	# JSON values pulled verbatim from upstream — ensure they survive too.
	assert addr["road"] == "Av. Corrientes"

	# Verify we hit Nominatim with the policy-mandated headers + email.
	call_kwargs = mock_get.call_args.kwargs
	assert "muse/" in call_kwargs["headers"]["User-Agent"]
	assert call_kwargs["params"]["email"]
