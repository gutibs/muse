"""What a stranger holding a share link is allowed to see.

The public serializers used to be the internal ones — `SharedListPublicSerializer`
reused `PinSerializer`, which nests the full `RestaurantSerializer`. That made
the anonymous payload a moving target: every field added anywhere upstream
appeared here without anyone deciding it should. These tests fix the payload
shape so that adding a field to an internal serializer can never widen the
public one silently.
"""

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from pins.models import Pin
from tests.factories import PinFactory, RestaurantFactory, SharedListFactory, UserFactory

# Fields that must never reach an unauthenticated caller. `google_place_id`
# is a free lookup key into our whole catalogue; `phone` and the exact
# coordinates are contact/location data the owner never chose to publish
# by sharing a list of restaurant names.
FORBIDDEN_RESTAURANT_FIELDS = (
	"googlePlaceId",
	"phone",
	"approvalStatus",
	"createdAt",
)


def _public_payload(owner, **list_kwargs):
	shared = SharedListFactory(user=owner, is_active=True, **list_kwargs)
	resp = APIClient().get(reverse("shared-list-public", kwargs={"token": shared.token}))
	assert resp.status_code == 200, resp.content
	return resp.json()


@pytest.mark.critical
@pytest.mark.django_db
def test_public_payload_does_not_expose_internal_restaurant_fields():
	owner = UserFactory()
	restaurant = RestaurantFactory(
		name="Kam's Roast",
		phone="+852 2520 1110",
		google_place_id="ChIJ_public_leak_test",
	)
	PinFactory(user=owner, restaurant=restaurant, status=Pin.Status.VISITED, rating=5)

	data = _public_payload(owner)
	body = str(data)

	assert data["pins"], "the fixture pin should be in the payload"
	restaurant_payload = data["pins"][0]["restaurantDetail"]
	for field in FORBIDDEN_RESTAURANT_FIELDS:
		assert field not in restaurant_payload, f"{field} leaked to an anonymous caller"
	assert "ChIJ_public_leak_test" not in body
	assert "+852 2520 1110" not in body


@pytest.mark.critical
@pytest.mark.django_db
def test_public_payload_keeps_what_the_page_actually_renders():
	"""The counterpart to the test above: locking the payload down must not
	break the shared page, which shows name, city and the owner's rating."""
	owner = UserFactory()
	restaurant = RestaurantFactory(name="Kam's Roast", city="Hong Kong")
	PinFactory(
		user=owner,
		restaurant=restaurant,
		status=Pin.Status.VISITED,
		rating=4,
		comment="Great char siu",
	)

	pin = _public_payload(owner)["pins"][0]

	assert pin["restaurantDetail"]["name"] == "Kam's Roast"
	assert pin["restaurantDetail"]["city"] == "Hong Kong"
	assert pin["rating"] == 4
	assert pin["comment"] == "Great char siu"
	assert pin["status"] == Pin.Status.VISITED


@pytest.mark.critical
@pytest.mark.django_db
def test_public_payload_is_capped():
	"""`get_pins` returned every pin the owner had, unpaginated, on an
	endpoint with no auth. A list with hundreds of pins made each anonymous
	request arbitrarily expensive."""
	from pins.serializers_public import PUBLIC_PIN_LIMIT

	owner = UserFactory()
	for _ in range(PUBLIC_PIN_LIMIT + 5):
		PinFactory(user=owner, restaurant=RestaurantFactory(), status=Pin.Status.TO_VISIT)

	assert len(_public_payload(owner)["pins"]) == PUBLIC_PIN_LIMIT


@pytest.mark.critical
@pytest.mark.django_db
def test_public_payload_still_honours_status_filter():
	owner = UserFactory()
	PinFactory(user=owner, restaurant=RestaurantFactory(), status=Pin.Status.TO_VISIT)
	PinFactory(user=owner, restaurant=RestaurantFactory(), status=Pin.Status.VISITED, rating=3)

	data = _public_payload(owner, status_filter=Pin.Status.VISITED)

	assert len(data["pins"]) == 1
	assert data["pins"][0]["status"] == Pin.Status.VISITED


@pytest.mark.critical
@pytest.mark.django_db
def test_public_payload_only_contains_the_owners_pins():
	owner = UserFactory()
	stranger = UserFactory()
	PinFactory(user=owner, restaurant=RestaurantFactory(name="Mine"), status=Pin.Status.TO_VISIT)
	PinFactory(
		user=stranger, restaurant=RestaurantFactory(name="Theirs"), status=Pin.Status.TO_VISIT
	)

	body = str(_public_payload(owner))

	assert "Mine" in body
	assert "Theirs" not in body
