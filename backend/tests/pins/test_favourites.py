"""Favoritos.

Es un flag del pin y no un tercer `Pin.Status`: `unique_together (user,
restaurant)` hace que marcar favorito pisaría el pin que ya está, y
`SharedList.status_filter` heredaría una opción que no es un estado. Tampoco
un modelo aparte: el producto ya obliga a pinear para opinar, así que el pin
es el lugar.

El detalle que parece cosmético y no lo es: `Pin.Meta.ordering` es
`["-updated_at"]` con `auto_now`, así que marcar un favorito con un PATCH
normal reordenaría la lista bajo el dedo de quien lo tocó.
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


@pytest.mark.django_db
def test_a_pin_starts_out_not_favourite():
	pin = PinFactory()
	assert pin.is_favourite is False


@pytest.mark.critical
@pytest.mark.django_db
def test_marking_and_unmarking_a_favourite():
	user = UserFactory()
	pin = PinFactory(user=user)
	url = reverse("pin-favourite", args=[pin.id])

	resp = _client(user).post(url, {"isFavourite": True}, format="json")
	assert resp.status_code == 200, resp.content
	pin.refresh_from_db()
	assert pin.is_favourite is True

	resp = _client(user).post(url, {"isFavourite": False}, format="json")
	assert resp.status_code == 200, resp.content
	pin.refresh_from_db()
	assert pin.is_favourite is False


@pytest.mark.critical
@pytest.mark.django_db
def test_marking_a_favourite_does_not_reorder_the_list():
	"""El bug que hace que la lista salte: `ordering` es `-updated_at` con
	`auto_now`, así que tocar la estrella mandaría ese pin al tope."""
	user = UserFactory()
	viejo = PinFactory(user=user, restaurant=RestaurantFactory())
	nuevo = PinFactory(user=user, restaurant=RestaurantFactory())
	antes = list(Pin.objects.filter(user=user).values_list("id", flat=True))
	updated_at_antes = Pin.objects.get(pk=viejo.pk).updated_at

	_client(user).post(
		reverse("pin-favourite", args=[viejo.id]), {"isFavourite": True}, format="json"
	)

	assert list(Pin.objects.filter(user=user).values_list("id", flat=True)) == antes
	assert Pin.objects.get(pk=viejo.pk).updated_at == updated_at_antes
	assert nuevo.id in antes


@pytest.mark.critical
@pytest.mark.django_db
def test_nobody_can_favourite_someone_elses_pin():
	ajeno = PinFactory(user=UserFactory())

	resp = _client(UserFactory()).post(
		reverse("pin-favourite", args=[ajeno.id]), {"isFavourite": True}, format="json"
	)

	assert resp.status_code == 404, resp.content
	ajeno.refresh_from_db()
	assert ajeno.is_favourite is False


@pytest.mark.django_db
def test_the_list_can_be_filtered_to_favourites():
	user = UserFactory()
	favorito = PinFactory(user=user, restaurant=RestaurantFactory(), is_favourite=True)
	PinFactory(user=user, restaurant=RestaurantFactory())

	resp = _client(user).get(reverse("pin-list"), {"favourite": "true"})

	assert resp.status_code == 200, resp.content
	assert [row["id"] for row in resp.json()["results"]] == [favorito.id]


@pytest.mark.django_db
def test_without_the_filter_everything_comes_back():
	user = UserFactory()
	PinFactory(user=user, restaurant=RestaurantFactory(), is_favourite=True)
	PinFactory(user=user, restaurant=RestaurantFactory())

	resp = _client(user).get(reverse("pin-list"))

	assert resp.json()["count"] == 2


@pytest.mark.django_db
def test_the_flag_travels_in_the_payload():
	user = UserFactory()
	PinFactory(user=user, is_favourite=True)

	resp = _client(user).get(reverse("pin-list"))

	assert resp.json()["results"][0]["isFavourite"] is True


@pytest.mark.critical
@pytest.mark.django_db
def test_a_favourite_is_not_exposed_on_a_shared_link():
	"""Marcar un favorito es una nota privada sobre el propio mapa, no algo
	que se publique con la lista."""
	from pins.models import SharedList
	from pins.serializers_public import SharedListPublicSerializer

	user = UserFactory()
	PinFactory(user=user, is_favourite=True, status=Pin.Status.VISITED, rating=5)
	lista = SharedList.objects.create(user=user, title="Mis lugares")

	data = SharedListPublicSerializer(lista).data

	assert "isFavourite" not in str(data)
	assert "is_favourite" not in str(data)
