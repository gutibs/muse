"""Server-side filtering on PinViewSet.

Backs the fix for the profile-page pagination bug: the frontend was reading
only the first page (PAGE_SIZE=20) and filtering locally, which lied about
counts for users with >20 pins. With server-side filtering, /pins/?status=X
returns the full filtered set across pages.
"""

import pytest
from rest_framework.test import APIClient

from pins.models import Pin
from tests.factories import PinFactory, RestaurantFactory, UserFactory


@pytest.mark.critical
@pytest.mark.django_db
def test_pin_filter_by_status():
	user = UserFactory()
	# 15 visited (with rating, required by serializer/model invariant)
	for _ in range(15):
		PinFactory(
			user=user,
			restaurant=RestaurantFactory(),
			status=Pin.Status.VISITED,
			rating=4,
		)
	# 10 to_visit (no rating allowed)
	for _ in range(10):
		PinFactory(
			user=user,
			restaurant=RestaurantFactory(),
			status=Pin.Status.TO_VISIT,
			rating=None,
		)

	client = APIClient()
	client.force_authenticate(user=user)

	# Visited filter — total count must be 15 (across pages), not 20.
	res = client.get("/api/v1/pins/?status=visited")
	assert res.status_code == 200, res.content
	assert res.data["count"] == 15
	assert all(p["status"] == "visited" for p in res.data["results"])

	# To-visit filter — total count must be 10.
	res = client.get("/api/v1/pins/?status=to_visit")
	assert res.status_code == 200
	assert res.data["count"] == 10
	assert all(p["status"] == "to_visit" for p in res.data["results"])

	# `status=all` is treated as no-filter (frontend can pass it explicitly).
	res = client.get("/api/v1/pins/?status=all")
	assert res.status_code == 200
	assert res.data["count"] == 25

	# No status param — also no-filter.
	res = client.get("/api/v1/pins/")
	assert res.status_code == 200
	assert res.data["count"] == 25

	# Pagination still works: first page returns at most PAGE_SIZE rows.
	page_one_results = res.data["results"]
	assert len(page_one_results) <= 20
