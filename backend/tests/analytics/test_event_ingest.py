"""El endpoint de ingesta es la única puerta abierta al cliente, y hay dos
cosas que no puede dejar pasar.

La primera es `save_to_map`: ese contador es la evidencia de negocio que se
le muestra a un tercero, y sale de un signal del servidor cuando el Pin se
crea de verdad. Si el endpoint lo aceptara, cualquiera con un token válido
podría inflarlo desde una consola.

La segunda son las props: un JSONField que el cliente llena a gusto termina
con datos personales adentro, y ahí la retención de 14 meses no protege
nada porque el dato ya no es el que declaramos en la política.
"""

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from analytics.models import Event
from tests.factories import RestaurantFactory, UserFactory


def _client(user=None):
	c = APIClient()
	if user is not None:
		c.force_authenticate(user=user)
	return c


def _url():
	return reverse("analytics-events")


@pytest.mark.critical
@pytest.mark.django_db
def test_client_cannot_report_save_to_map():
	"""El contador de negocio no se acepta desde el cliente."""
	user = UserFactory()
	restaurant = RestaurantFactory()

	resp = _client(user).post(
		_url(),
		{"events": [{"name": "save_to_map", "restaurant": restaurant.id}]},
		format="json",
	)

	assert resp.status_code == 400, resp.content
	assert Event.objects.count() == 0


@pytest.mark.critical
@pytest.mark.django_db
def test_unknown_props_are_rejected():
	"""Una clave fuera de la whitelist es un 400, no un campo que se guarda
	callado: así no entra PII por la ventana del JSONField."""
	user = UserFactory()
	restaurant = RestaurantFactory()

	resp = _client(user).post(
		_url(),
		{
			"events": [
				{
					"name": "venue_card_view",
					"restaurant": restaurant.id,
					"props": {"email": "someone@example.com"},
				}
			]
		},
		format="json",
	)

	assert resp.status_code == 400, resp.content
	assert Event.objects.count() == 0


@pytest.mark.django_db
def test_requires_authentication():
	restaurant = RestaurantFactory()

	resp = _client().post(
		_url(),
		{"events": [{"name": "venue_card_view", "restaurant": restaurant.id}]},
		format="json",
	)

	assert resp.status_code == 401, resp.content
	assert Event.objects.count() == 0


@pytest.mark.django_db
def test_accepts_a_batch_and_stamps_the_user():
	user = UserFactory()
	one, two = RestaurantFactory(), RestaurantFactory()

	resp = _client(user).post(
		_url(),
		{
			"events": [
				{"name": "venue_card_view", "restaurant": one.id, "props": {"surface": "feed"}},
				{"name": "venue_detail_view", "restaurant": two.id},
			]
		},
		format="json",
	)

	assert resp.status_code == 201, resp.content
	assert resp.json()["accepted"] == 2
	assert Event.objects.filter(user=user).count() == 2
	card = Event.objects.get(name=Event.Name.VENUE_CARD_VIEW)
	assert card.restaurant_id == one.id
	assert card.props == {"surface": "feed"}


@pytest.mark.django_db
def test_external_click_requires_a_destination():
	"""Sin destino el evento no dice nada: el reporte que ve Jess agrupa
	justamente por destino."""
	user = UserFactory()
	restaurant = RestaurantFactory()

	resp = _client(user).post(
		_url(),
		{"events": [{"name": "external_action_click", "restaurant": restaurant.id}]},
		format="json",
	)

	assert resp.status_code == 400, resp.content
	assert Event.objects.count() == 0


@pytest.mark.django_db
def test_view_events_require_a_restaurant():
	user = UserFactory()

	resp = _client(user).post(
		_url(),
		{"events": [{"name": "venue_card_view"}]},
		format="json",
	)

	assert resp.status_code == 400, resp.content


@pytest.mark.django_db
def test_batch_is_capped():
	"""Un cliente con un bug no puede mandar diez mil filas en un POST."""
	user = UserFactory()
	restaurant = RestaurantFactory()
	events = [{"name": "venue_card_view", "restaurant": restaurant.id}] * 51

	resp = _client(user).post(_url(), {"events": events}, format="json")

	assert resp.status_code == 400, resp.content
	assert Event.objects.count() == 0


@pytest.mark.django_db
def test_a_bad_event_rejects_the_whole_batch():
	"""Todo o nada: aceptar la mitad de un batch deja al cliente sin saber
	qué reintentar, y reintentar duplica lo ya guardado."""
	user = UserFactory()
	restaurant = RestaurantFactory()

	resp = _client(user).post(
		_url(),
		{
			"events": [
				{"name": "venue_card_view", "restaurant": restaurant.id},
				{"name": "save_to_map", "restaurant": restaurant.id},
			]
		},
		format="json",
	)

	assert resp.status_code == 400, resp.content
	assert Event.objects.count() == 0
