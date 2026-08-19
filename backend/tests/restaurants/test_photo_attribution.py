"""Atribución del autor de la foto en el detalle del restaurante.

Los Google Maps Platform Terms exigen mostrar el autor junto a la foto que
servimos. El dato sale del payload de details que ya está cacheado —no se
guarda una segunda copia en el Restaurant— y se expone sólo en el detalle:
en el listado obligaría a un lookup por fila.
"""

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from places.models import PlaceDetailsCache
from tests.factories import RestaurantFactory, UserFactory

PLACE_ID = "ChIJN1t_tDeuEmsRUsoyG83frY4"
REF = f"places/{PLACE_ID}/photos/AeJbb3f"
ATTRIBUTIONS = [{"displayName": "Ana P.", "uri": "https://maps.google.com/ana"}]


def _client():
	client = APIClient()
	client.force_authenticate(user=UserFactory())
	return client


@pytest.mark.django_db
def test_detail_exposes_the_photo_attribution():
	restaurant = RestaurantFactory(photo_ref=REF, google_place_id=PLACE_ID)
	PlaceDetailsCache.objects.create(
		place_id=PLACE_ID,
		field_mask="id,photos",
		payload={"photos": [{"name": REF, "authorAttributions": ATTRIBUTIONS}]},
		fetched_at=timezone.now(),
	)

	res = _client().get(f"/api/v1/restaurants/{restaurant.id}/")

	assert res.status_code == 200
	assert res.json()["photoAttribution"] == ATTRIBUTIONS


@pytest.mark.django_db
def test_restaurant_without_photo_has_an_empty_attribution():
	restaurant = RestaurantFactory(photo_ref="", image_url="")

	res = _client().get(f"/api/v1/restaurants/{restaurant.id}/")

	assert res.status_code == 200
	assert res.json()["photoAttribution"] == []


@pytest.mark.django_db
def test_list_does_not_carry_the_attribution():
	# Un lookup por fila en un listado paginado es un N+1; la decisión de
	# producto fue mostrar el crédito sólo en el detalle.
	RestaurantFactory(photo_ref=REF)

	res = _client().get("/api/v1/restaurants/")

	assert res.status_code == 200
	assert "photoAttribution" not in res.json()["results"][0]
