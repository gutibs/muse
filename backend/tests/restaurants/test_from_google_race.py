"""Race-condition test for RestaurantViewSet.from_google.

The threaded variant (two real HTTP threads hitting the same place_id) is
flaky against pytest-django's transactional fixtures: each thread needs its
own DB connection and the test runner has to coordinate teardown carefully.
We use the functional-equivalent fallback documented in the task spec:
pre-create a Restaurant, force the initial existence lookup to miss, and
verify the IntegrityError except-branch (restaurants/services/google_import.py)
finds the duplicate row and returns it instead of creating a second one.

Post-B-006 the fetch + race fallback live in the service module, not the
view, so we patch `restaurants.services.google_import.requests.get`.
"""

from unittest.mock import patch

import pytest
from django.contrib.gis.geos import Point
from django.urls import reverse
from rest_framework.test import APIClient

from restaurants.models import Restaurant
from tests.factories import UserFactory

GOOGLE_PAYLOAD = {
	"id": "ChIJ_test_place_123",
	"displayName": {"text": "Race Test Restaurant"},
	"formattedAddress": "123 Test Street, Buenos Aires",
	"location": {"latitude": -34.60, "longitude": -58.38},
	"addressComponents": [
		{"types": ["locality"], "longText": "Buenos Aires"},
		{"types": ["country"], "longText": "Argentina"},
	],
	"websiteUri": "https://example.com",
	"internationalPhoneNumber": "+54 11 1234-5678",
	"regularOpeningHours": {"weekdayDescriptions": []},
	"photos": [],
}


class _FakeGoogleResponse:
	status_code = 200

	def raise_for_status(self):
		pass

	def json(self):
		return GOOGLE_PAYLOAD


@pytest.mark.critical
@pytest.mark.slow
@pytest.mark.django_db(transaction=True)
def test_from_google_race_creates_single_restaurant(settings):
	"""Simulate the race: two requests for the same placeId, the first miss
	on the SELECT, an existing row already in the DB → IntegrityError →
	fallback path returns the existing row, no duplicate is created."""
	settings.GOOGLE_PLACES_API_KEY = "test-key"
	place_id = GOOGLE_PAYLOAD["id"]

	# Pre-existing row (as if a sibling thread inserted it between our SELECT
	# and our INSERT).
	user = UserFactory()
	pre_existing = Restaurant.objects.create(
		name="Race Test Restaurant",
		location=Point(-58.38, -34.60, srid=4326),
		google_place_id=place_id,
		approval_status=Restaurant.ApprovalStatus.APPROVED,
		created_by=user,
	)

	client = APIClient()
	client.force_authenticate(user=user)

	# Force the initial existence lookup to return None so the code falls
	# through to the create-and-catch-IntegrityError path. The lookup at
	# line 149 of restaurants/views.py is `Restaurant.objects.filter(...).first()`.
	# We monkey-patch the manager's `filter` for that single attribute access.
	original_filter = Restaurant.objects.filter
	call_count = {"n": 0}

	def filter_first_call_returns_empty(*args, **kwargs):
		call_count["n"] += 1
		# Only short-circuit the very first lookup (the existence check at
		# the top of from_google). Subsequent filters (the except branch's
		# recovery lookup, the _base_queryset annotation, etc.) must work.
		if call_count["n"] == 1 and kwargs.get("google_place_id") == place_id:

			class _Empty:
				def first(self):
					return None

			return _Empty()
		return original_filter(*args, **kwargs)

	url = reverse("restaurant-from-google")
	with patch.object(Restaurant.objects, "filter", side_effect=filter_first_call_returns_empty):
		with patch(
			"restaurants.services.google_import.requests.get",
			return_value=_FakeGoogleResponse(),
		):
			response = client.post(url, data={"placeId": place_id}, format="json")

	# Recovery path returned the existing restaurant (200) instead of creating
	# a duplicate (which would have been 201 with a fresh id).
	assert response.status_code == 200, response.content
	assert response.data["id"] == pre_existing.id

	# The hard guarantee: still exactly one row for that place_id.
	assert Restaurant.objects.filter(google_place_id=place_id).count() == 1
