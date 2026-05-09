"""Profile.dietary_preferences API surface (post C-007).

Replaces the legacy free-text `dietary` CharField with an M2M to a closed
set of choices. Frontend can no longer send arbitrary strings.
"""

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.models import DietaryPreference
from tests.factories import UserFactory


def _client(user):
	c = APIClient()
	c.force_authenticate(user=user)
	return c


@pytest.mark.critical
@pytest.mark.django_db
def test_dietary_preferences_endpoint_lists_canonical_5():
	"""The 5 seeded preferences are exposed through the public list endpoint."""
	res = _client(UserFactory()).get(reverse("dietary_preferences"))
	assert res.status_code == 200
	body = res.json()
	names = sorted(p["name"] for p in body)
	assert names == ["Gluten-free", "Kosher", "Omnivore", "Vegan", "Vegetarian"]


@pytest.mark.critical
@pytest.mark.django_db
def test_profile_patch_accepts_valid_dietary_preference_ids():
	user = UserFactory()
	vegan = DietaryPreference.objects.get(slug="vegan")
	gf = DietaryPreference.objects.get(slug="gluten-free")

	res = _client(user).patch(
		reverse("profile"),
		data={"dietaryPreferences": [vegan.id, gf.id]},
		format="json",
	)
	assert res.status_code == 200, res.content

	user.refresh_from_db()
	stored_slugs = sorted(user.profile.dietary_preferences.values_list("slug", flat=True))
	assert stored_slugs == ["gluten-free", "vegan"]

	# Detail field is rendered with name/slug for the frontend.
	detail = res.json()["dietaryPreferencesDetail"]
	assert sorted(d["slug"] for d in detail) == ["gluten-free", "vegan"]


@pytest.mark.critical
@pytest.mark.django_db
def test_profile_patch_rejects_unknown_dietary_preference_id():
	user = UserFactory()
	# 99999 is far beyond the 5 seeded rows.
	res = _client(user).patch(
		reverse("profile"),
		data={"dietaryPreferences": [99999]},
		format="json",
	)
	assert res.status_code == 400
	# DRF surfaces the field name as the camelCase key it received.
	assert "dietaryPreferences" in res.json()


@pytest.mark.critical
@pytest.mark.django_db
def test_profile_patch_clears_dietary_preferences_with_empty_list():
	user = UserFactory()
	vegan = DietaryPreference.objects.get(slug="vegan")
	user.profile.dietary_preferences.add(vegan)

	res = _client(user).patch(
		reverse("profile"),
		data={"dietaryPreferences": []},
		format="json",
	)
	assert res.status_code == 200
	user.refresh_from_db()
	assert user.profile.dietary_preferences.count() == 0
