"""F2.A — las seis superficies que muestran pins ajenos.

La política está probada en `test_visibility_levels.py`. Acá se prueba que
cada superficie la usa: son los seis puntos que el mapeo del spec encontró
mostrando pins sin ninguna noción de privacidad.
"""

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.models import Friendship
from pins.models import Pin, SharedList, SharedListItem
from tests.factories import (
	FriendshipFactory,
	PinFactory,
	RestaurantFactory,
	SharedListFactory,
	UserFactory,
)


def _befriend(a, b):
	return FriendshipFactory(from_user=a, to_user=b, status=Friendship.Status.ACCEPTED)


def _client(user=None):
	client = APIClient()
	if user:
		client.force_authenticate(user=user)
	return client


@pytest.mark.critical
@pytest.mark.django_db
def test_a_friends_pin_list_hides_the_private_ones():
	viewer, owner = UserFactory(), UserFactory()
	_befriend(viewer, owner)
	shown = PinFactory(
		user=owner, restaurant=RestaurantFactory(name="Shown"), visibility=Pin.Visibility.FRIENDS
	)
	PinFactory(
		user=owner, restaurant=RestaurantFactory(name="Hidden"), visibility=Pin.Visibility.PRIVATE
	)

	resp = _client(viewer).get(reverse("user_pins", kwargs={"user_id": owner.id}))

	assert resp.status_code == 200, resp.content
	assert [p["id"] for p in resp.json()] == [shown.id]


@pytest.mark.critical
@pytest.mark.django_db
def test_the_restaurant_reviews_hide_a_private_pin():
	"""D-001 sigue en pie para los pins públicos —que son el default— pero
	deja de valer para el que su autor restringió."""
	viewer, owner = UserFactory(), UserFactory()
	restaurant = RestaurantFactory()
	PinFactory(
		user=owner,
		restaurant=restaurant,
		status=Pin.Status.VISITED,
		rating=5,
		comment="Fui con mi psicóloga",
		visibility=Pin.Visibility.PRIVATE,
	)

	resp = _client(viewer).get(reverse("restaurant-detail", args=[restaurant.id]))

	assert resp.status_code == 200, resp.content
	assert resp.json()["reviews"] == []


@pytest.mark.critical
@pytest.mark.django_db
def test_the_restaurant_reviews_keep_a_public_pin_from_a_stranger():
	viewer, owner = UserFactory(), UserFactory()
	restaurant = RestaurantFactory()
	pin = PinFactory(
		user=owner,
		restaurant=restaurant,
		status=Pin.Status.VISITED,
		rating=5,
		comment="Excelente",
		visibility=Pin.Visibility.PUBLIC,
	)

	resp = _client(viewer).get(reverse("restaurant-detail", args=[restaurant.id]))

	assert [r["id"] for r in resp.json()["reviews"]] == [pin.id]


@pytest.mark.critical
@pytest.mark.django_db
def test_a_friends_only_review_is_hidden_from_a_stranger_and_shown_to_a_friend():
	friend, stranger, owner = UserFactory(), UserFactory(), UserFactory()
	_befriend(friend, owner)
	restaurant = RestaurantFactory()
	pin = PinFactory(
		user=owner,
		restaurant=restaurant,
		status=Pin.Status.VISITED,
		rating=4,
		comment="Sólo para mis amigos",
		visibility=Pin.Visibility.FRIENDS,
	)

	url = reverse("restaurant-detail", args=[restaurant.id])
	assert _client(stranger).get(url).json()["reviews"] == []
	assert [r["id"] for r in _client(friend).get(url).json()["reviews"]] == [pin.id]


@pytest.mark.critical
@pytest.mark.django_db
def test_friend_stats_leave_out_a_friends_private_pin():
	"""Decisión 2.bis del spec: el promedio "de tus amigos" se calcula sobre
	pocos datos. Con un solo amigo pineado, ese número *es* el rating de esa
	persona, así que un pin privado ahí lo publicaría."""
	viewer, friend = UserFactory(), UserFactory()
	_befriend(viewer, friend)
	restaurant = RestaurantFactory()
	PinFactory(
		user=friend,
		restaurant=restaurant,
		status=Pin.Status.VISITED,
		rating=5,
		visibility=Pin.Visibility.PRIVATE,
	)

	stats = (
		_client(viewer)
		.get(reverse("restaurant-detail", args=[restaurant.id]))
		.json()["friendStats"]
	)

	assert stats["ratingAvg"] is None
	assert stats["ratedCount"] == 0


@pytest.mark.critical
@pytest.mark.django_db
def test_friend_stats_still_count_a_friends_pin_they_kept_for_friends():
	viewer, friend = UserFactory(), UserFactory()
	_befriend(viewer, friend)
	restaurant = RestaurantFactory()
	PinFactory(
		user=friend,
		restaurant=restaurant,
		status=Pin.Status.VISITED,
		rating=4,
		visibility=Pin.Visibility.FRIENDS,
	)

	stats = (
		_client(viewer)
		.get(reverse("restaurant-detail", args=[restaurant.id]))
		.json()["friendStats"]
	)

	assert stats["ratingAvg"] == 4.0
	assert stats["ratedCount"] == 1


@pytest.mark.critical
@pytest.mark.django_db
def test_the_restaurant_average_is_the_same_number_for_everyone():
	"""Decisión 2 del spec, y por eso este test no verifica un filtro sino su
	ausencia: el promedio y el conteo del restaurante incluyen los pins
	privados, para que la ficha no diga un número distinto según quién mire.
	El día que alguien "arregle" esto filtrando por visibilidad, esto se pone
	en rojo y lo manda a leer la decisión."""
	owner, friend, stranger = UserFactory(), UserFactory(), UserFactory()
	_befriend(friend, owner)
	restaurant = RestaurantFactory()
	PinFactory(
		user=owner,
		restaurant=restaurant,
		status=Pin.Status.VISITED,
		rating=2,
		visibility=Pin.Visibility.PRIVATE,
	)

	url = reverse("restaurant-detail", args=[restaurant.id])
	vistas = [_client(u).get(url).json() for u in (owner, friend, stranger)]

	assert [v["averageRating"] for v in vistas] == [2.0, 2.0, 2.0]
	assert [v["pinCount"] for v in vistas] == [1, 1, 1]


@pytest.mark.critical
@pytest.mark.django_db
def test_the_feed_drops_an_activity_whose_pin_turned_private():
	"""Decisión 4 del spec: aunque la Activity ya haya ocurrido y el amigo la
	haya visto. El feed serializa el pin en su estado actual, así que dejarla
	mostraría el comentario de un pin privado con su rating al día."""
	viewer, friend = UserFactory(), UserFactory()
	_befriend(viewer, friend)
	pin = PinFactory(user=friend, restaurant=RestaurantFactory())

	antes = _client(viewer).get(reverse("feed")).json()["results"]
	assert [row["pin"]["id"] for row in antes if row["pin"]] == [pin.id]

	pin.visibility = Pin.Visibility.PRIVATE
	pin.save()

	despues = _client(viewer).get(reverse("feed")).json()["results"]
	assert [row["pin"]["id"] for row in despues if row["pin"]] == []


@pytest.mark.critical
@pytest.mark.django_db
def test_the_feed_keeps_activities_that_have_no_pin():
	"""La actividad de amistad no cuelga de ningún pin. Filtrar por
	visibilidad sin contemplarla vaciaría media pantalla."""
	viewer, friend = UserFactory(), UserFactory()
	_befriend(viewer, friend)
	otro = UserFactory()
	_befriend(friend, otro)

	rows = _client(viewer).get(reverse("feed")).json()["results"]

	assert any(row["verb"] == "friendship" for row in rows)


@pytest.mark.critical
@pytest.mark.django_db
def test_a_shared_link_only_shows_public_pins():
	"""El visitante de un link es un desconocido sin sesión: sólo ve lo
	público. Un pin `friends` no entra —no hay amistad que verificar— y uno
	`private` tampoco."""
	owner = UserFactory()
	publico = PinFactory(
		user=owner, restaurant=RestaurantFactory(name="Público"), visibility=Pin.Visibility.PUBLIC
	)
	PinFactory(
		user=owner, restaurant=RestaurantFactory(name="Amigos"), visibility=Pin.Visibility.FRIENDS
	)
	PinFactory(
		user=owner, restaurant=RestaurantFactory(name="Privado"), visibility=Pin.Visibility.PRIVATE
	)
	lista = SharedListFactory(user=owner)

	resp = APIClient().get(reverse("shared-list-public", args=[lista.token]))

	assert resp.status_code == 200, resp.content
	nombres = [p["restaurantDetail"]["name"] for p in resp.json()["pins"]]
	assert nombres == [publico.restaurant.name]


@pytest.mark.critical
@pytest.mark.django_db
def test_a_curated_list_cannot_publish_a_private_pin():
	"""Decisión 3 del spec: elegirlo a mano no lo convierte en compartible.
	Si se lo quiere en la lista, primero se le cambia el nivel."""
	owner = UserFactory()
	privado = PinFactory(
		user=owner, restaurant=RestaurantFactory(name="Privado"), visibility=Pin.Visibility.PRIVATE
	)
	publico = PinFactory(
		user=owner, restaurant=RestaurantFactory(name="Público"), visibility=Pin.Visibility.PUBLIC
	)
	lista = SharedListFactory(user=owner, kind=SharedList.Kind.CURATED)
	SharedListItem.objects.create(shared_list=lista, pin=privado, position=0)
	SharedListItem.objects.create(shared_list=lista, pin=publico, position=1)

	resp = APIClient().get(reverse("shared-list-public", args=[lista.token]))

	nombres = [p["restaurantDetail"]["name"] for p in resp.json()["pins"]]
	assert nombres == [publico.restaurant.name]


@pytest.mark.critical
@pytest.mark.django_db
def test_the_profile_counters_count_what_the_viewer_can_see():
	"""Un amigo no puede ver "42 lugares" y una lista de 30: el contador es
	cardinalidad, y filtra igual que el listado."""
	viewer, owner = UserFactory(), UserFactory()
	_befriend(viewer, owner)
	PinFactory(
		user=owner,
		restaurant=RestaurantFactory(),
		status=Pin.Status.VISITED,
		rating=5,
		visibility=Pin.Visibility.FRIENDS,
	)
	PinFactory(
		user=owner,
		restaurant=RestaurantFactory(),
		status=Pin.Status.VISITED,
		rating=1,
		visibility=Pin.Visibility.PRIVATE,
	)

	stats = (
		_client(viewer).get(reverse("public_profile", kwargs={"user_id": owner.id})).json()["stats"]
	)

	assert stats["pinCount"] == 1
	assert stats["visitedCount"] == 1


@pytest.mark.critical
@pytest.mark.django_db
def test_the_owner_still_sees_all_of_their_own_pins_in_their_counters():
	owner = UserFactory()
	PinFactory(user=owner, restaurant=RestaurantFactory(), visibility=Pin.Visibility.PRIVATE)
	PinFactory(user=owner, restaurant=RestaurantFactory(), visibility=Pin.Visibility.PUBLIC)

	stats = _client(owner).get(reverse("profile")).json()["stats"]

	assert stats["pinCount"] == 2
