"""RestaurantViewSet.nearby — coordinate parsing must answer 400, not 500.

`float(lat)` ran unguarded, so `?lat=abc` raised ValueError out of the view
and Django turned it into a 500. `radius` had no ceiling either, so
`?radius=100000` scanned the whole table. Both are trivially reachable from
a malformed client request.
"""

import pytest
from django.contrib.gis.geos import Point
from django.urls import reverse
from rest_framework.test import APIClient

from tests.factories import RestaurantFactory, UserFactory

URL = reverse("restaurant-nearby")


def _client():
	c = APIClient()
	c.force_authenticate(user=UserFactory())
	return c


@pytest.mark.parametrize(
	"query",
	[
		"lat=abc&lng=2",  # non-numeric lat
		"lat=1&lng=xyz",  # non-numeric lng
		"lat=&lng=",  # empty
		"lat=1",  # lng missing
		"lng=1",  # lat missing
		"lat=100&lng=0",  # lat out of range
		"lat=0&lng=200",  # lng out of range
		"lat=0&lng=0&radius=abc",  # non-numeric radius
		"lat=0&lng=0&radius=0",  # non-positive radius
		"lat=0&lng=0&radius=-5",
	],
)
@pytest.mark.django_db
def test_nearby_rejects_bad_coordinates_with_400(query):
	resp = _client().get(f"{URL}?{query}")
	assert resp.status_code == 400, f"{query} → {resp.status_code}: {resp.content}"


@pytest.mark.django_db
def test_nearby_returns_restaurants_within_radius():
	near = RestaurantFactory(name="Near", location=Point(-58.38, -34.60, srid=4326))
	RestaurantFactory(name="Far", location=Point(2.35, 48.85, srid=4326))  # Paris

	resp = _client().get(f"{URL}?lat=-34.60&lng=-58.38&radius=5")

	assert resp.status_code == 200, resp.content
	names = [r["name"] for r in resp.json()]
	assert names == [near.name]


@pytest.mark.django_db
def test_nearby_caps_an_oversized_radius_instead_of_scanning_the_planet():
	"""An absurd radius is clamped, not honoured: the query stays bounded and
	the caller still gets a sensible answer."""
	RestaurantFactory(name="Near", location=Point(-58.38, -34.60, srid=4326))
	RestaurantFactory(name="Paris", location=Point(2.35, 48.85, srid=4326))

	resp = _client().get(f"{URL}?lat=-34.60&lng=-58.38&radius=100000")

	assert resp.status_code == 200, resp.content
	names = [r["name"] for r in resp.json()]
	assert "Near" in names
	assert "Paris" not in names
