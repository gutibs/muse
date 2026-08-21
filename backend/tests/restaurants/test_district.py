"""El distrito sale del payload que ya pedimos.

Google manda `sublocality` en `addressComponents` y los dos parsers lo
tiraban. Es el dato con el que la gente ubica un lugar en Hong Kong —Sheung
Wan, Central— y en Buenos Aires —Palermo, Chacarita—, mucho más que la
ciudad, que para todo el catálogo porteño dice lo mismo.

Cero llamadas nuevas: el campo viene en la misma respuesta.
"""

from unittest.mock import patch

import pytest
from django.core.management import call_command

from restaurants.services import google_import
from tests.factories import RestaurantFactory

PAYLOAD = {
	"id": "ChIJtest",
	"displayName": {"text": "Yardbird"},
	"location": {"latitude": 22.28, "longitude": 114.15},
	"addressComponents": [
		{"longText": "Sheung Wan", "types": ["sublocality_level_1", "sublocality"]},
		{"longText": "Hong Kong", "types": ["locality"]},
		{"longText": "Hong Kong", "types": ["country"]},
	],
}


@pytest.mark.django_db
def test_importing_stores_the_district():
	from tests.factories import UserFactory

	with patch.object(google_import, "get_details", return_value=PAYLOAD):
		restaurant, _ = google_import.import_from_google_place_id("ChIJtest", UserFactory())

	assert restaurant.district == "Sheung Wan"
	assert restaurant.city == "Hong Kong"


@pytest.mark.django_db
def test_the_backfill_fills_only_what_is_missing():
	sin_distrito = RestaurantFactory(name="Yardbird", google_place_id="ChIJtest", district="")
	ya_tiene = RestaurantFactory(name="Otro", google_place_id="ChIJotro", district="Palermo")

	with patch(
		"restaurants.management.commands.backfill_districts.get_details",
		return_value=PAYLOAD,
	) as get_details:
		call_command("backfill_districts")

	sin_distrito.refresh_from_db()
	ya_tiene.refresh_from_db()
	assert sin_distrito.district == "Sheung Wan"
	# El que ya tenía distrito no se vuelve a pedir: cada llamada evitada es
	# una llamada facturable menos y el cap gratuito son 1.000 por mes.
	assert ya_tiene.district == "Palermo"
	assert get_details.call_count == 1


@pytest.mark.django_db
def test_the_backfill_skips_restaurants_without_a_place_id():
	"""Un restaurante cargado a mano no tiene a quién preguntarle."""
	RestaurantFactory(name="A mano", google_place_id=None, district="")

	with patch("restaurants.management.commands.backfill_districts.get_details") as get_details:
		call_command("backfill_districts")

	assert get_details.call_count == 0


@pytest.mark.django_db
def test_the_backfill_has_a_dry_run():
	restaurant = RestaurantFactory(google_place_id="ChIJtest", district="")

	with patch(
		"restaurants.management.commands.backfill_districts.get_details",
		return_value=PAYLOAD,
	):
		call_command("backfill_districts", "--dry-run")

	restaurant.refresh_from_db()
	assert restaurant.district == ""


@pytest.mark.django_db
def test_the_backfill_survives_one_bad_response():
	"""550 restaurantes y uno que falla no puede tirar abajo la corrida."""
	roto = RestaurantFactory(name="Roto", google_place_id="ChIJroto", district="")
	sano = RestaurantFactory(name="Sano", google_place_id="ChIJtest", district="")

	def responder(place_id, *args, **kwargs):
		if place_id == "ChIJroto":
			raise RuntimeError("Google says no")
		return PAYLOAD

	with patch(
		"restaurants.management.commands.backfill_districts.get_details",
		side_effect=responder,
	):
		call_command("backfill_districts")

	roto.refresh_from_db()
	sano.refresh_from_db()
	assert roto.district == ""
	assert sano.district == "Sheung Wan"


@pytest.mark.django_db
def test_the_public_payload_carries_the_district():
	from pins.serializers_public import PublicRestaurantSerializer

	restaurant = RestaurantFactory(district="Sheung Wan")

	assert PublicRestaurantSerializer(restaurant).data["district"] == "Sheung Wan"


@pytest.mark.django_db
def test_a_restaurant_without_district_serialises_as_empty_string():
	restaurant = RestaurantFactory(district="")
	from pins.serializers_public import PublicRestaurantSerializer

	assert PublicRestaurantSerializer(restaurant).data["district"] == ""


def test_district_is_not_a_new_google_call():
	"""El field mask ya pide addressComponents: agregar distrito no agrega
	un solo request."""
	from restaurants.services.google_place_parser import FIELD_MASK

	assert "addressComponents" in FIELD_MASK


@pytest.mark.django_db
def test_the_backfill_also_marks_the_attributes():
	"""El payload ya está en la mano: leerlo para el distrito y no aprovechar
	los atributos dejaba la autoselección sin efecto sobre todo lo que ya
	estaba en el catálogo."""
	from restaurants.models import Tag

	restaurant = RestaurantFactory(name="Con terraza", google_place_id="ChIJtest", district="")

	payload = dict(PAYLOAD, outdoorSeating=True, allowsDogs=True, liveMusic=False)
	with patch(
		"restaurants.management.commands.backfill_districts.get_details",
		return_value=payload,
	):
		call_command("backfill_districts")

	restaurant.refresh_from_db()
	assert restaurant.district == "Sheung Wan"
	assert set(restaurant.tags.values_list("slug", flat=True)) == {
		"outdoor-terrace",
		"pet-friendly",
	}
	assert Tag.objects.get(slug="live-music") not in restaurant.tags.all()


@pytest.mark.django_db
def test_a_restaurant_with_a_district_still_gets_its_attributes():
	"""El corte de "ya tiene distrito" no puede dejar afuera los atributos:
	son dos datos distintos del mismo payload."""
	restaurant = RestaurantFactory(
		name="Ya ubicado", google_place_id="ChIJtest", district="Palermo"
	)

	payload = dict(PAYLOAD, outdoorSeating=True)
	with patch(
		"restaurants.management.commands.backfill_districts.get_details",
		return_value=payload,
	):
		call_command("backfill_districts", "--attributes")

	restaurant.refresh_from_db()
	assert restaurant.district == "Palermo"
	assert set(restaurant.tags.values_list("slug", flat=True)) == {"outdoor-terrace"}


@pytest.mark.django_db
def test_the_dry_run_does_not_mark_attributes_either():
	restaurant = RestaurantFactory(google_place_id="ChIJtest", district="")

	with patch(
		"restaurants.management.commands.backfill_districts.get_details",
		return_value=dict(PAYLOAD, outdoorSeating=True),
	):
		call_command("backfill_districts", "--dry-run")

	restaurant.refresh_from_db()
	assert restaurant.tags.count() == 0
