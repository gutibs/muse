"""F1.7 — qué hace el badge de Insider en las superficies de restaurantes.

Dos cosas distintas: el filtro `?insider=true`, que cambia **qué**
restaurantes se listan, y el orden de las reseñas, que cambia **cuál se lee
primero** sin sacar ninguna.

El filtro es el que tiene filo. "Restaurantes donde pineó un Insider" se
responde mirando pins, así que si el subquery no pasa por la misma política
de visibilidad que el resto, el listado delata pins privados: el restaurante
aparece, y aparece *porque* alguien lo pineó en secreto.
"""

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from pins.constants import Visibility
from pins.models import Pin
from tests.factories import PinFactory, RestaurantFactory, UserFactory


def _auth(user):
	client = APIClient()
	client.force_authenticate(user=user)
	return client


def _insider(username="insider"):
	user = UserFactory(username=username)
	user.profile.is_verified_insider = True
	user.profile.save()
	return user


def _names(resp):
	return {row["name"] for row in resp.json()["results"]}


# --- El filtro --------------------------------------------------------------


@pytest.mark.django_db
def test_the_filter_keeps_only_places_an_insider_pinned():
	insider = _insider()
	anyone = UserFactory(username="anyone")
	recommended = RestaurantFactory(name="Recomendado")
	other = RestaurantFactory(name="Cualquiera")
	PinFactory(user=insider, restaurant=recommended, visibility=Visibility.PUBLIC)
	PinFactory(user=anyone, restaurant=other, visibility=Visibility.PUBLIC)

	resp = _auth(UserFactory(username="viewer")).get(
		reverse("restaurant-list"), {"insider": "true"}
	)

	assert _names(resp) == {"Recomendado"}


@pytest.mark.django_db
def test_without_the_filter_nothing_changes():
	insider = _insider()
	anyone = UserFactory(username="anyone")
	PinFactory(user=insider, restaurant=RestaurantFactory(name="Recomendado"))
	PinFactory(user=anyone, restaurant=RestaurantFactory(name="Cualquiera"))

	resp = _auth(UserFactory(username="viewer")).get(reverse("restaurant-list"))

	assert _names(resp) == {"Recomendado", "Cualquiera"}


@pytest.mark.django_db
def test_a_place_pinned_twice_by_insiders_appears_once():
	first, second = _insider("one"), _insider("two")
	shared = RestaurantFactory(name="Compartido")
	PinFactory(user=first, restaurant=shared, visibility=Visibility.PUBLIC)
	PinFactory(user=second, restaurant=shared, visibility=Visibility.PUBLIC)

	resp = _auth(UserFactory(username="viewer")).get(
		reverse("restaurant-list"), {"insider": "true"}
	)

	assert [row["name"] for row in resp.json()["results"]] == ["Compartido"]


@pytest.mark.critical
@pytest.mark.django_db
def test_the_filter_does_not_leak_a_private_pin():
	"""El oráculo: el restaurante aparecería *porque* hay un pin escondido."""
	insider = _insider()
	secret = RestaurantFactory(name="Secreto")
	PinFactory(user=insider, restaurant=secret, visibility=Visibility.PRIVATE)

	resp = _auth(UserFactory(username="stranger")).get(
		reverse("restaurant-list"), {"insider": "true"}
	)

	assert _names(resp) == set(), "un pin privado se dedujo desde el filtro"


@pytest.mark.critical
@pytest.mark.django_db
def test_a_friends_only_pin_reaches_a_friend_and_nobody_else():
	from accounts.models import Friendship

	insider = _insider()
	friend = UserFactory(username="friend")
	stranger = UserFactory(username="stranger")
	Friendship.objects.create(from_user=insider, to_user=friend, status=Friendship.Status.ACCEPTED)
	place = RestaurantFactory(name="Para amigos")
	PinFactory(user=insider, restaurant=place, visibility=Visibility.FRIENDS)

	seen_by_friend = _auth(friend).get(reverse("restaurant-list"), {"insider": "true"})
	seen_by_stranger = _auth(stranger).get(reverse("restaurant-list"), {"insider": "true"})

	assert _names(seen_by_friend) == {"Para amigos"}
	assert _names(seen_by_stranger) == set()


@pytest.mark.django_db
def test_the_filter_combines_with_the_city_filter():
	"""Ejes distintos se cruzan con AND, como los que ya existían."""
	insider = _insider()
	PinFactory(
		user=insider,
		restaurant=RestaurantFactory(name="Acá", city="Hong Kong"),
		visibility=Visibility.PUBLIC,
	)
	PinFactory(
		user=insider,
		restaurant=RestaurantFactory(name="Allá", city="Buenos Aires"),
		visibility=Visibility.PUBLIC,
	)

	resp = _auth(UserFactory(username="viewer")).get(
		reverse("restaurant-list"), {"insider": "true", "city": "Hong Kong"}
	)

	assert _names(resp) == {"Acá"}


# --- El orden de las reseñas ------------------------------------------------


@pytest.mark.django_db
def test_an_insider_review_is_read_before_a_stranger_s():
	insider = _insider()
	anyone = UserFactory(username="anyone")
	restaurant = RestaurantFactory()
	# El del desconocido es el más reciente: sin el criterio nuevo iría arriba.
	PinFactory(
		user=insider,
		restaurant=restaurant,
		status=Pin.Status.VISITED,
		rating=5,
		comment="Del insider",
		visibility=Visibility.PUBLIC,
	)
	PinFactory(
		user=anyone,
		restaurant=restaurant,
		status=Pin.Status.VISITED,
		rating=3,
		comment="De cualquiera",
		visibility=Visibility.PUBLIC,
	)

	resp = _auth(UserFactory(username="viewer")).get(
		reverse("restaurant-detail", kwargs={"pk": restaurant.pk})
	)

	comments = [r["comment"] for r in resp.json()["reviews"]]
	assert comments == ["Del insider", "De cualquiera"]


@pytest.mark.django_db
def test_a_friend_still_comes_before_an_insider_stranger():
	"""El orden por amistad es una decisión anterior y no se deroga acá.

	Insider ordena *dentro* de cada grupo: primero la gente que conocés,
	después la que Muse verificó.
	"""
	from accounts.models import Friendship

	me = UserFactory(username="me")
	friend = UserFactory(username="friend")
	insider = _insider()
	Friendship.objects.create(from_user=me, to_user=friend, status=Friendship.Status.ACCEPTED)
	restaurant = RestaurantFactory()
	PinFactory(
		user=insider,
		restaurant=restaurant,
		status=Pin.Status.VISITED,
		rating=5,
		comment="Del insider",
		visibility=Visibility.PUBLIC,
	)
	PinFactory(
		user=friend,
		restaurant=restaurant,
		status=Pin.Status.VISITED,
		rating=4,
		comment="De mi amiga",
		visibility=Visibility.PUBLIC,
	)

	resp = _auth(me).get(reverse("restaurant-detail", kwargs={"pk": restaurant.pk}))

	comments = [r["comment"] for r in resp.json()["reviews"]]
	assert comments == ["De mi amiga", "Del insider"]


@pytest.mark.django_db
def test_the_review_carries_the_badge():
	insider = _insider()
	restaurant = RestaurantFactory()
	PinFactory(
		user=insider,
		restaurant=restaurant,
		status=Pin.Status.VISITED,
		rating=5,
		comment="Vale la pena",
		visibility=Visibility.PUBLIC,
	)

	resp = _auth(UserFactory(username="viewer")).get(
		reverse("restaurant-detail", kwargs={"pk": restaurant.pk})
	)

	assert resp.json()["reviews"][0]["user"]["isVerifiedInsider"] is True
