"""Google nos dice cuándo un lugar cerró; hasta ahora no se lo preguntábamos.

`businessStatus` viaja en el mismo payload de Place Details. Sin pedirlo, dos
restaurantes estuvieron cuatro años cerrados en el catálogo sin que nadie se
enterara. Con esto, mantener el catálogo deja de depender de que alguien
lea el diario.
"""

from unittest.mock import patch

import pytest
from django.core.management import call_command

from restaurants.services import google_import
from restaurants.services.google_place_parser import FIELD_MASK, parse_place
from tests.factories import RestaurantFactory, UserFactory

BASE = {
	"id": "ChIJcerrado",
	"displayName": {"text": "Tegui"},
	"location": {"latitude": -34.6, "longitude": -58.4},
}


def test_the_mask_asks_for_the_business_status():
	assert "businessStatus" in FIELD_MASK


@pytest.mark.parametrize(
	"status,cerrado",
	[
		("CLOSED_PERMANENTLY", True),
		# Un cierre temporal no es un cierre: reabre y el lugar tiene que
		# volver a aparecer solo, sin que nadie lo destilde a mano.
		("CLOSED_TEMPORARILY", False),
		("OPERATIONAL", False),
		# Google no siempre lo manda.
		(None, False),
	],
)
def test_parse_place_reads_the_status(status, cerrado):
	payload = dict(BASE)
	if status is not None:
		payload["businessStatus"] = status

	assert parse_place(payload)["is_closed"] is cerrado


@pytest.mark.django_db
def test_importing_a_closed_place_marks_it():
	payload = dict(BASE, businessStatus="CLOSED_PERMANENTLY")

	with patch.object(google_import, "get_details", return_value=payload):
		restaurant, _ = google_import.import_from_google_place_id("ChIJcerrado", UserFactory())

	assert restaurant.is_closed is True


@pytest.mark.critical
@pytest.mark.django_db
def test_from_google_does_not_resurrect_a_closed_restaurant():
	"""El importador devuelve la fila existente sin volver a mirar Google, así
	que un lugar cerrado se podía traer de vuelta desde el autocomplete y
	pinear como si nada."""
	from django.urls import reverse
	from rest_framework.test import APIClient

	cerrado = RestaurantFactory(name="Tegui", google_place_id="ChIJcerrado", is_closed=True)
	client = APIClient()
	client.force_authenticate(user=UserFactory())

	resp = client.post(reverse("restaurant-from-google"), {"placeId": "ChIJcerrado"}, format="json")

	assert resp.status_code == 409, resp.content
	assert resp.json()["restaurantId"] == cerrado.id


@pytest.mark.django_db
def test_the_backfill_marks_places_google_reports_as_closed():
	restaurant = RestaurantFactory(name="Tegui", google_place_id="ChIJcerrado", district="X")

	with patch(
		"restaurants.management.commands.backfill_from_google.get_details",
		return_value=dict(BASE, businessStatus="CLOSED_PERMANENTLY"),
	):
		call_command("backfill_from_google", "--attributes")

	restaurant.refresh_from_db()
	assert restaurant.is_closed is True


@pytest.mark.django_db
def test_the_backfill_does_not_reopen_what_someone_closed_by_hand():
	"""Tegui e i Latina se marcan a mano porque no tienen place_id. Si el
	backfill destildara lo que Google no confirma, los volvería a abrir."""
	restaurant = RestaurantFactory(
		name="i Latina", google_place_id="ChIJabierto", district="X", is_closed=True
	)

	with patch(
		"restaurants.management.commands.backfill_from_google.get_details",
		return_value=dict(BASE, businessStatus="OPERATIONAL"),
	):
		call_command("backfill_from_google", "--attributes")

	restaurant.refresh_from_db()
	assert restaurant.is_closed is True
