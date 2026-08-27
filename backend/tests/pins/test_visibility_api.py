"""F2.A — elegir el nivel desde la app.

La política y las superficies no sirven de nada si el dueño de un pin no
tiene cómo cambiarlo: estos son los dos campos que la app escribe.
"""

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.models import Friendship
from pins.models import Pin
from tests.factories import (
	FriendshipFactory,
	PinFactory,
	RestaurantFactory,
	UserFactory,
)


def _client(user):
	client = APIClient()
	client.force_authenticate(user=user)
	return client


@pytest.mark.critical
@pytest.mark.django_db
def test_the_owner_can_restrict_a_pin_they_already_created():
	owner = UserFactory()
	pin = PinFactory(user=owner, restaurant=RestaurantFactory())

	resp = _client(owner).patch(
		reverse("pin-detail", args=[pin.id]), {"visibility": "private"}, format="json"
	)

	assert resp.status_code == 200, resp.content
	pin.refresh_from_db()
	assert pin.visibility == Pin.Visibility.PRIVATE


@pytest.mark.django_db
def test_a_new_pin_can_choose_its_level_and_defaults_to_inheriting():
	owner = UserFactory()
	restaurant = RestaurantFactory()

	resp = _client(owner).post(
		reverse("pin-list"),
		{"restaurant": restaurant.id, "status": "to_visit", "visibility": "friends"},
		format="json",
	)
	assert resp.status_code == 201, resp.content
	assert resp.json()["visibility"] == "friends"

	otro = _client(owner).post(
		reverse("pin-list"),
		{"restaurant": RestaurantFactory().id, "status": "to_visit"},
		format="json",
	)
	assert otro.status_code == 201, otro.content
	# NULL, no "public": el pin hereda el default del perfil en vez de
	# congelar el valor que tenía al crearse.
	assert otro.json()["visibility"] is None


@pytest.mark.django_db
def test_an_unknown_level_is_rejected():
	owner = UserFactory()
	pin = PinFactory(user=owner, restaurant=RestaurantFactory())

	resp = _client(owner).patch(
		reverse("pin-detail", args=[pin.id]), {"visibility": "secreto"}, format="json"
	)

	assert resp.status_code == 400, resp.content


@pytest.mark.critical
@pytest.mark.django_db
def test_the_profile_default_can_be_changed_and_moves_the_inherited_pins():
	# El viewer tiene que ser amigo: sin amistad, `UserPinsView` contesta 403
	# antes de mirar un solo pin y el test no probaría la herencia.
	owner, viewer = UserFactory(), UserFactory()
	FriendshipFactory(from_user=viewer, to_user=owner, status=Friendship.Status.ACCEPTED)
	heredado = PinFactory(user=owner, restaurant=RestaurantFactory(), visibility=None)

	resp = _client(owner).patch(
		reverse("profile"), {"defaultPinVisibility": "private"}, format="json"
	)

	assert resp.status_code == 200, resp.content
	owner.profile.refresh_from_db()
	assert owner.profile.default_pin_visibility == Pin.Visibility.PRIVATE

	visibles = _client(viewer).get(reverse("user_pins", kwargs={"user_id": owner.id}))
	assert heredado.id not in [p["id"] for p in visibles.json()]
