"""Los tres ejes de la taxonomía.

Vibe (cómo se siente el lugar), Occasion (para qué vas) y Scene (qué tiene)
viven en un solo modelo `Tag`, distinguidos por `kind`. Antes eran dos
modelos en dos apps: `Tag` en restaurants y `Persona` en pins, con la misma
semántica y sin forma de combinarlos en un filtro.

Se siembran por migración y no por fixture a propósito: `make seed` nunca
corrió en producción, y por eso ahí había cuatro tags mientras el fixture
declaraba doce.
"""

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from pins.models import Pin
from restaurants.models import Tag
from tests.factories import RestaurantFactory, UserFactory


def _client(user):
	c = APIClient()
	c.force_authenticate(user=user)
	return c


@pytest.mark.critical
@pytest.mark.django_db
def test_the_three_axes_are_seeded_by_migration():
	"""Sin esto, producción queda con tres grupos vacíos y el usuario no
	tiene una sola etiqueta que elegir."""
	assert Tag.objects.filter(kind=Tag.Kind.VIBE).count() == 7
	assert Tag.objects.filter(kind=Tag.Kind.SCENE).count() == 5
	assert Tag.objects.filter(kind=Tag.Kind.OCCASION).count() == 12


@pytest.mark.django_db
@pytest.mark.parametrize(
	"slug,kind",
	[
		("quiet", Tag.Kind.VIBE),
		("fine-dining", Tag.Kind.VIBE),
		("outdoor-terrace", Tag.Kind.SCENE),
		("live-music", Tag.Kind.SCENE),
		("pet-friendly", Tag.Kind.SCENE),
		("date-night", Tag.Kind.OCCASION),
		("brunch", Tag.Kind.OCCASION),
		("solo-dining", Tag.Kind.OCCASION),
	],
)
def test_known_tags_land_on_the_right_axis(slug, kind):
	"""Los doce que ya existían mezclaban dos ejes: Quiet es un vibe y
	Outdoor / Terrace es una característica del lugar."""
	assert Tag.objects.get(slug=slug).kind == kind


@pytest.mark.critical
@pytest.mark.django_db
def test_the_tag_endpoint_filters_by_axis():
	"""Sin `?kind=`, la pantalla de vibe ofrecía `vegetarian` y
	`gluten-free`, que son dietary."""
	client = _client(UserFactory())

	resp = client.get(reverse("tag-list"), {"kind": "vibe"})

	assert resp.status_code == 200, resp.content
	# El endpoint no pagina a propósito: son dos docenas de etiquetas y el
	# cliente las quiere todas de una para pintar los tres grupos.
	assert {row["kind"] for row in resp.json()} == {"vibe"}


@pytest.mark.django_db
def test_the_tag_endpoint_still_returns_everything_without_a_filter():
	client = _client(UserFactory())

	resp = client.get(reverse("tag-list"))

	assert resp.status_code == 200, resp.content
	assert len(resp.json()) >= 24


@pytest.mark.critical
@pytest.mark.django_db
def test_a_pin_carries_tags_from_the_three_axes():
	user = UserFactory()
	restaurant = RestaurantFactory()
	tags = [
		Tag.objects.get(slug="romantic"),
		Tag.objects.get(slug="date-night"),
		Tag.objects.get(slug="live-music"),
	]

	resp = _client(user).post(
		reverse("pin-list"),
		{
			"restaurant": restaurant.id,
			"status": "visited",
			"rating": 5,
			"tagIds": [t.id for t in tags],
		},
		format="json",
	)

	assert resp.status_code == 201, resp.content
	pin = Pin.objects.get(user=user, restaurant=restaurant)
	assert set(pin.tags.values_list("slug", flat=True)) == {
		"romantic",
		"date-night",
		"live-music",
	}
	assert {t["kind"] for t in resp.json()["tagsDetail"]} == {"vibe", "occasion", "scene"}


@pytest.mark.django_db
def test_pins_can_be_filtered_by_tag_slug():
	user = UserFactory()
	wanted = RestaurantFactory()
	other = RestaurantFactory()
	date_night = Tag.objects.get(slug="date-night")

	pin = Pin.objects.create(user=user, restaurant=wanted, status=Pin.Status.TO_VISIT)
	pin.tags.add(date_night)
	Pin.objects.create(user=user, restaurant=other, status=Pin.Status.TO_VISIT)

	resp = _client(user).get(reverse("pin-list"), {"tag": "date-night"})

	assert resp.status_code == 200, resp.content
	assert [row["restaurant"] for row in resp.json()["results"]] == [wanted.id]
