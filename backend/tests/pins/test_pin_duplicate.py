"""Pinning the same restaurant twice must answer 409, not 500.

(user, restaurant) is unique. PinViewSet.create catches IntegrityError to
turn that collision into a 409 carrying the existing pin id, so the app can
send the user straight to the edit screen. That path was dead: Pin.save()
called full_clean(), whose validate_unique() raised Django's ValidationError
before the INSERT ever reached the database, and DRF does not translate that
exception — the user got a bare 500 on an everyday action ("I already had
this one").
"""

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from pins.models import Pin
from tests.factories import PinFactory, RestaurantFactory, UserFactory


def _client(user):
	c = APIClient()
	c.force_authenticate(user=user)
	return c


@pytest.mark.critical
@pytest.mark.django_db
def test_pinning_same_restaurant_twice_returns_409_with_existing_id():
	user = UserFactory()
	restaurant = RestaurantFactory()
	client = _client(user)
	payload = {"restaurant": restaurant.id, "status": "to_visit"}

	first = client.post(reverse("pin-list"), payload, format="json")
	assert first.status_code == 201, first.content

	second = client.post(reverse("pin-list"), payload, format="json")
	assert second.status_code == 409, second.content
	assert second.json()["pinId"] == first.json()["id"]
	assert Pin.objects.filter(user=user, restaurant=restaurant).count() == 1


@pytest.mark.django_db
def test_same_restaurant_pinned_by_two_users_is_allowed():
	"""Uniqueness is per (user, restaurant) — two people pinning the same
	place is the normal case, not a collision."""
	restaurant = RestaurantFactory()
	payload = {"restaurant": restaurant.id, "status": "to_visit"}

	for user in (UserFactory(), UserFactory()):
		resp = _client(user).post(reverse("pin-list"), payload, format="json")
		assert resp.status_code == 201, resp.content

	assert Pin.objects.filter(restaurant=restaurant).count() == 2


@pytest.mark.django_db
def test_status_rating_invariant_still_returns_400_not_409():
	"""The duplicate path must not swallow the other validation: an invalid
	status/rating combo is a 400 about the field, not a conflict."""
	user = UserFactory()
	resp = _client(user).post(
		reverse("pin-list"),
		{"restaurant": RestaurantFactory().id, "status": "visited"},
		format="json",
	)
	assert resp.status_code == 400, resp.content
	assert "rating" in resp.json()


@pytest.mark.django_db
def test_updating_own_pin_is_not_treated_as_duplicate():
	"""PATCHing an existing pin re-saves a row whose (user, restaurant) already
	exists — that must not be mistaken for a collision."""
	user = UserFactory()
	pin = PinFactory(user=user, status=Pin.Status.TO_VISIT)

	resp = _client(user).patch(
		reverse("pin-detail", kwargs={"pk": pin.pk}),
		{"status": "visited", "rating": 5},
		format="json",
	)
	assert resp.status_code == 200, resp.content
	pin.refresh_from_db()
	assert pin.status == Pin.Status.VISITED
	assert pin.rating == 5
