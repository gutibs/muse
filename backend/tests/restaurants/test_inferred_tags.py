"""Etiquetas que Google ya sabe y el usuario no debería tener que tildar.

Si el payload dice que el lugar tiene terraza, música en vivo o acepta
perros, la pantalla puede venir con esos chips marcados. Es una sugerencia
del sistema sobre un hecho del local —no sobre el gusto de nadie— y por eso
se puede pre-marcar sin mentirle a nadie.

El costo es cero: los campos viven en el SKU Enterprise + Atmosphere, pero
el cap gratuito es de 1.000 llamadas por SKU y por mes, y con la caché de 30
días el techo del catálogo son ~550 (verificado contra la doc oficial y una
llamada real el 2026-08-19).
"""

import pytest

from restaurants.services.google_place_parser import FIELD_MASK, inferred_tag_slugs


def test_the_mask_asks_for_the_atmosphere_fields():
	for field in ("outdoorSeating", "liveMusic", "allowsDogs"):
		assert field in FIELD_MASK


@pytest.mark.parametrize(
	"payload,esperado",
	[
		({"outdoorSeating": True}, {"outdoor-terrace"}),
		({"liveMusic": True}, {"live-music"}),
		({"allowsDogs": True}, {"pet-friendly"}),
		(
			{"outdoorSeating": True, "liveMusic": True, "allowsDogs": True},
			{"outdoor-terrace", "live-music", "pet-friendly"},
		),
	],
)
def test_a_true_attribute_becomes_its_tag(payload, esperado):
	assert inferred_tag_slugs(payload) == esperado


@pytest.mark.parametrize(
	"payload",
	[
		# False es una respuesta: Google sabe que no tiene terraza.
		{"outdoorSeating": False, "liveMusic": False, "allowsDogs": False},
		# Ausente es otra cosa: Google no sabe. Tampoco se marca.
		{},
		# Y un valor que no es booleano no se interpreta.
		{"outdoorSeating": "yes", "liveMusic": None},
	],
)
def test_nothing_is_inferred_without_a_true(payload):
	assert inferred_tag_slugs(payload) == set()


def test_only_known_attributes_are_mapped():
	"""Un atributo nuevo de Google no inventa una etiqueta que no existe en
	el catálogo: el chip quedaría marcado apuntando a la nada."""
	assert inferred_tag_slugs({"servesWine": True, "goodForChildren": True}) == set()


def test_the_inference_is_a_pure_function():
	"""Sin red y sin base: se puede testear con un payload de mentira, que es
	la única forma de cubrir combinaciones que Google rara vez devuelve."""
	payload = {"outdoorSeating": True}
	assert inferred_tag_slugs(payload) == inferred_tag_slugs(payload)
	assert payload == {"outdoorSeating": True}, "no debe mutar lo que recibe"


@pytest.mark.django_db
def test_importing_marks_the_attributes_on_the_restaurant():
	"""Los atributos son del local, no de quien lo guarda: viven en
	`Restaurant.tags` y de ahí los toma la pantalla de pin para pre-marcar
	los chips."""
	from unittest.mock import patch

	from restaurants.services import google_import
	from tests.factories import UserFactory

	payload = {
		"id": "ChIJinferido",
		"displayName": {"text": "Bar con terraza"},
		"location": {"latitude": -34.6, "longitude": -58.38},
		"outdoorSeating": True,
		"allowsDogs": True,
		"liveMusic": False,
	}

	with patch.object(google_import, "get_details", return_value=payload):
		restaurant, _ = google_import.import_from_google_place_id("ChIJinferido", UserFactory())

	assert set(restaurant.tags.values_list("slug", flat=True)) == {
		"outdoor-terrace",
		"pet-friendly",
	}


@pytest.mark.django_db
def test_a_known_place_is_not_re_evaluated():
	"""Un place que ya está en el catálogo no se vuelve a pedir: el
	importador corta antes, y por eso tampoco puede pisar las etiquetas que
	alguien haya marcado a mano en el admin."""
	from unittest.mock import patch

	from restaurants.models import Tag
	from restaurants.services import google_import
	from tests.factories import RestaurantFactory, UserFactory

	restaurant = RestaurantFactory(name="Ya existe", google_place_id="ChIJinferido")
	restaurant.tags.add(Tag.objects.get(slug="vegetarian"))

	with patch.object(google_import, "get_details") as get_details:
		devuelto, creado = google_import.import_from_google_place_id("ChIJinferido", UserFactory())

	assert creado is False
	assert get_details.call_count == 0
	assert devuelto.id == restaurant.id
	assert set(devuelto.tags.values_list("slug", flat=True)) == {"vegetarian"}
