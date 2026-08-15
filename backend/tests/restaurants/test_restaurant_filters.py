"""Restaurant filtering through the FilterSet.

Two of these are regressions. django-filter was installed and declared as a
global backend but never ran on this viewset: `list` was overridden and
skipped `filter_queryset()`, and `nearby` used the bare queryset, so
combining "near me" with any filter silently ignored the filter.
"""

import pytest
from django.contrib.gis.geos import Point
from django.urls import reverse
from rest_framework.test import APIClient

from restaurants.models import Restaurant
from tests.factories import CuisineFactory, RestaurantFactory, UserFactory

# Obelisco, and a point ~40 km away — far enough to fall outside any sane
# default radius, close enough to stay in the same projection sanity zone.
NEAR = (-58.3816, -34.6037)
FAR = (-58.8, -34.9)


@pytest.fixture
def client():
	c = APIClient()
	c.force_authenticate(user=UserFactory())
	return c


def _restaurant(name, *, lng_lat=NEAR, city="Buenos Aires", cuisines=()):
	r = RestaurantFactory(
		name=name,
		city=city,
		location=Point(*lng_lat, srid=4326),
		approval_status=Restaurant.ApprovalStatus.APPROVED,
	)
	if cuisines:
		r.cuisines.set([CuisineFactory(name=c) for c in cuisines])
	return r


@pytest.mark.django_db
def test_search_filters_by_name(client):
	_restaurant("Kam's Roast")
	_restaurant("Pizza Cero")

	resp = client.get(reverse("restaurant-list"), {"search": "kam"})

	assert resp.status_code == 200, resp.content
	assert [r["name"] for r in resp.json()["results"]] == ["Kam's Roast"]


@pytest.mark.django_db
def test_cuisine_accepts_several_slugs_and_matches_any(client):
	italian = CuisineFactory(name="Italian")
	japanese = CuisineFactory(name="Japanese")
	thai = CuisineFactory(name="Thai")
	a = _restaurant("Trattoria")
	a.cuisines.set([italian])
	b = _restaurant("Sushi Bar")
	b.cuisines.set([japanese])
	c = _restaurant("Bangkok")
	c.cuisines.set([thai])

	resp = client.get(reverse("restaurant-list"), {"cuisine": f"{italian.slug},{japanese.slug}"})

	names = sorted(r["name"] for r in resp.json()["results"])
	assert names == ["Sushi Bar", "Trattoria"]


@pytest.mark.django_db
def test_matching_several_cuisines_does_not_duplicate_the_row(client):
	"""Without distinct=True the join produces one row per matching cuisine."""
	italian = CuisineFactory(name="Italian")
	japanese = CuisineFactory(name="Japanese")
	fusion = _restaurant("Fusion")
	fusion.cuisines.set([italian, japanese])

	resp = client.get(reverse("restaurant-list"), {"cuisine": f"{italian.slug},{japanese.slug}"})

	assert len(resp.json()["results"]) == 1


@pytest.mark.django_db
def test_nearby_can_be_combined_with_a_filter(client):
	"""Regression: nearby used the unfiltered queryset, so ?search= alongside
	?lat= was ignored and every nearby restaurant came back."""
	_restaurant("Kam's Roast")
	_restaurant("Pizza Cero")

	resp = client.get(
		reverse("restaurant-nearby"),
		{"lat": NEAR[1], "lng": NEAR[0], "radius": 5, "search": "kam"},
	)

	assert resp.status_code == 200, resp.content
	assert [r["name"] for r in resp.json()] == ["Kam's Roast"]


@pytest.mark.django_db
def test_nearby_still_excludes_far_restaurants(client):
	_restaurant("Close By", lng_lat=NEAR)
	_restaurant("Far Away", lng_lat=FAR)

	resp = client.get(reverse("restaurant-nearby"), {"lat": NEAR[1], "lng": NEAR[0], "radius": 5})

	assert [r["name"] for r in resp.json()] == ["Close By"]


@pytest.mark.django_db
def test_list_is_ordered_so_pagination_is_stable(client):
	"""The endpoint paginates, and an unordered queryset lets PostgreSQL return
	rows in any order — a row could show up on two pages or on none.

	Meta.ordering alone does not fix it: Django drops the model's default
	ordering on querysets with an aggregate annotation, and this one annotates
	average_rating and pin_count. Hence the explicit order_by in
	_base_queryset.
	"""
	for name in ("Charlie", "Alpha", "Bravo"):
		_restaurant(name)

	names = [r["name"] for r in client.get(reverse("restaurant-list")).json()["results"]]

	assert names == ["Alpha", "Bravo", "Charlie"]


@pytest.mark.django_db
def test_ordering_survives_the_aggregate_annotation():
	"""Guards the specific Django behaviour above: if someone drops the
	explicit order_by trusting Meta.ordering, this catches it in the SQL."""
	from restaurants.views import RestaurantViewSet

	sql = str(RestaurantViewSet()._base_queryset().query)

	assert "ORDER BY" in sql


@pytest.mark.django_db
def test_pending_restaurants_stay_hidden_from_regular_users(client):
	"""The approval filter lives in get_queryset, so it must survive the move
	to filter_queryset."""
	RestaurantFactory(name="Pending One", approval_status=Restaurant.ApprovalStatus.PENDING)
	_restaurant("Approved One")

	resp = client.get(reverse("restaurant-list"), {"search": "One"})

	assert [r["name"] for r in resp.json()["results"]] == ["Approved One"]
