import uuid

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from tests.factories import SharedListFactory, UserFactory


@pytest.mark.critical
@pytest.mark.django_db
def test_shared_list_public_view_404_on_inactive_or_invalid():
	owner = UserFactory()
	client = APIClient()  # public endpoint, no auth

	# 1) Inactive shared list → 404
	inactive = SharedListFactory(user=owner, is_active=False)
	url_inactive = reverse("shared-list-public", kwargs={"token": inactive.token})
	resp = client.get(url_inactive)
	assert resp.status_code == 404

	# 2) Random non-existent token → 404
	random_token = uuid.uuid4()
	url_missing = reverse("shared-list-public", kwargs={"token": random_token})
	resp = client.get(url_missing)
	assert resp.status_code == 404

	# 3) Active shared list → 200 with payload
	active = SharedListFactory(user=owner, is_active=True, title="My Faves")
	url_active = reverse("shared-list-public", kwargs={"token": active.token})
	resp = client.get(url_active)
	assert resp.status_code == 200, resp.content
	data = resp.json()
	assert data["title"] == "My Faves"
	# camelCase renderer; pins is exposed as `pins` in either casing
	assert "pins" in data
