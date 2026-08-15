"""The pin selector and the visibility policy.

The bug these lock down: `?status=all` meant "no filter" on
`/api/v1/pins/` and a literal status value on `/api/v1/users/<id>/pins/`,
so the same query string returned a friend's whole list on one endpoint
and an empty list on the other.
"""

import pytest
from django.urls import reverse
from rest_framework.exceptions import PermissionDenied
from rest_framework.test import APIClient

from accounts.models import Friendship
from accounts.services.visibility import can_view, require_can_view, visible_user_ids
from pins.models import Pin
from pins.selectors import visible_pins
from tests.factories import FriendshipFactory, PinFactory, RestaurantFactory, UserFactory


def _befriend(a, b):
	return FriendshipFactory(from_user=a, to_user=b, status=Friendship.Status.ACCEPTED)


@pytest.mark.django_db
def test_status_all_is_treated_as_no_filter():
	user = UserFactory()
	PinFactory(user=user, restaurant=RestaurantFactory(), status=Pin.Status.TO_VISIT)
	PinFactory(user=user, restaurant=RestaurantFactory(), status=Pin.Status.VISITED, rating=4)

	assert visible_pins(user, status="all").count() == 2
	assert visible_pins(user, status=None).count() == 2
	assert visible_pins(user, status=Pin.Status.VISITED).count() == 1


@pytest.mark.critical
@pytest.mark.django_db
def test_friend_pins_endpoint_honours_status_all():
	"""Regression: this endpoint used to pass "all" through as a literal
	status value, so a friend's list came back empty."""
	viewer, owner = UserFactory(), UserFactory()
	_befriend(viewer, owner)
	PinFactory(user=owner, restaurant=RestaurantFactory(), status=Pin.Status.TO_VISIT)
	PinFactory(user=owner, restaurant=RestaurantFactory(), status=Pin.Status.VISITED, rating=5)

	client = APIClient()
	client.force_authenticate(user=viewer)
	resp = client.get(reverse("user_pins", kwargs={"user_id": owner.id}), {"status": "all"})

	assert resp.status_code == 200, resp.content
	assert len(resp.json()) == 2


@pytest.mark.django_db
def test_selector_defaults_to_the_viewers_own_pins():
	user, other = UserFactory(), UserFactory()
	PinFactory(user=user, restaurant=RestaurantFactory(name="Mine"))
	PinFactory(user=other, restaurant=RestaurantFactory(name="Theirs"))

	names = [p.restaurant.name for p in visible_pins(user)]

	assert names == ["Mine"]


@pytest.mark.critical
@pytest.mark.django_db
def test_can_view_is_symmetric_and_only_counts_accepted():
	a, b, stranger = UserFactory(), UserFactory(), UserFactory()
	_befriend(a, b)

	assert can_view(a, b)
	assert can_view(b, a)
	assert can_view(a, a), "your own data is always yours"
	assert not can_view(a, stranger)


@pytest.mark.critical
@pytest.mark.django_db
def test_pending_friendship_does_not_grant_visibility():
	a, b = UserFactory(), UserFactory()
	FriendshipFactory(from_user=a, to_user=b, status=Friendship.Status.PENDING)

	assert not can_view(a, b)
	assert not can_view(b, a)


@pytest.mark.critical
@pytest.mark.django_db
def test_anonymous_viewer_can_see_nothing():
	from django.contrib.auth.models import AnonymousUser

	assert not can_view(AnonymousUser(), UserFactory())
	assert visible_user_ids(AnonymousUser()) == set()


@pytest.mark.critical
@pytest.mark.django_db
def test_visible_user_ids_includes_the_viewer():
	"""Unlike friend_ids, which excludes them. Forgetting this is how a feed
	ends up hiding your own activity."""
	a, b, stranger = UserFactory(), UserFactory(), UserFactory()
	_befriend(a, b)

	ids = visible_user_ids(a)

	assert ids == {a.id, b.id}
	assert stranger.id not in ids


@pytest.mark.django_db
def test_require_can_view_raises_for_strangers_and_passes_for_friends():
	a, b, stranger = UserFactory(), UserFactory(), UserFactory()
	_befriend(a, b)

	require_can_view(a, b)  # must not raise

	with pytest.raises(PermissionDenied):
		require_can_view(a, stranger)
