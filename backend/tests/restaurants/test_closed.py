"""Un restaurante que cerró desaparece de las listas y sobrevive en los pins.

Dos restaurantes del catálogo llevaban cuatro años cerrados y seguían
saliendo en la búsqueda, con pins de "quiero ir" encima. No se pueden borrar:
`Pin.restaurant` es CASCADE y se llevaría las reseñas de la gente. Tampoco
sirve `approval_status=rejected`, que además de significar otra cosa haría
que la ficha diera 404 a cualquiera que no lo hubiera creado — o sea, a todos
los que tienen el pin.

De ahí la forma de esto: se oculta donde alguien podría descubrirlo, y se
conserva donde alguien ya lo tiene.
"""

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from pins.models import Pin
from tests.factories import RestaurantFactory, UserFactory


def _client(user):
	c = APIClient()
	c.force_authenticate(user=user)
	return c


@pytest.mark.critical
@pytest.mark.django_db
def test_a_closed_restaurant_is_not_in_the_list():
	RestaurantFactory(name="Tegui", is_closed=True)
	abierto = RestaurantFactory(name="Trescha", is_closed=False)

	resp = _client(UserFactory()).get(reverse("restaurant-list"))

	assert resp.status_code == 200, resp.content
	nombres = [row["name"] for row in resp.json()["results"]]
	assert nombres == [abierto.name]


@pytest.mark.critical
@pytest.mark.django_db
def test_a_closed_restaurant_is_not_in_nearby():
	"""`nearby` es el otro camino por el que se descubre un lugar."""
	RestaurantFactory(name="Tegui", is_closed=True)

	resp = _client(UserFactory()).get(
		reverse("restaurant-nearby"), {"lat": -34.60, "lng": -58.38, "radius": 20}
	)

	assert resp.status_code == 200, resp.content
	assert [row["name"] for row in resp.json()] == []


@pytest.mark.critical
@pytest.mark.django_db
def test_the_detail_of_a_closed_restaurant_still_answers():
	"""El invariante que protege los pins ajenos: si el detalle diera 404, el
	pin de cualquier otro usuario se rompería al tocarlo."""
	cerrado = RestaurantFactory(name="Tegui", is_closed=True)
	alguien_mas = UserFactory()

	resp = _client(alguien_mas).get(reverse("restaurant-detail", args=[cerrado.id]))

	assert resp.status_code == 200, resp.content
	assert resp.json()["isClosed"] is True


@pytest.mark.critical
@pytest.mark.django_db
def test_the_pin_of_a_closed_restaurant_survives():
	user = UserFactory()
	cerrado = RestaurantFactory(name="i Latina", is_closed=True)
	Pin.objects.create(user=user, restaurant=cerrado, status=Pin.Status.VISITED, rating=5)

	resp = _client(user).get(reverse("pin-list"))

	assert resp.status_code == 200, resp.content
	fila = resp.json()["results"][0]
	assert fila["restaurantDetail"]["name"] == "i Latina"
	assert fila["restaurantDetail"]["isClosed"] is True
	assert fila["rating"] == 5


@pytest.mark.django_db
def test_staff_still_sees_closed_restaurants(django_user_model):
	"""Alguien tiene que poder encontrarlos para administrarlos."""
	RestaurantFactory(name="Tegui", is_closed=True)
	staff = django_user_model.objects.create_user(
		username="staff-cerrados", email="staff@example.com", password="x", is_staff=True
	)

	resp = _client(staff).get(reverse("restaurant-list"))

	assert [row["name"] for row in resp.json()["results"]] == ["Tegui"]


@pytest.mark.critical
@pytest.mark.django_db
def test_a_user_cannot_reopen_a_restaurant_through_the_api():
	"""`is_closed` es un dato del catálogo, no algo que edite quien lo creó."""
	user = UserFactory()
	cerrado = RestaurantFactory(name="Tegui", is_closed=True, created_by=user)

	resp = _client(user).patch(
		reverse("restaurant-detail", args=[cerrado.id]),
		{"isClosed": False},
		format="json",
	)

	cerrado.refresh_from_db()
	assert cerrado.is_closed is True, resp.content
