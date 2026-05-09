"""MenuItem tags surface (post C-005).

Replaces the 3 boolean flags (is_vegetarian, is_gluten_free,
is_recommended) with a Tag M2M. There is no standalone
/restaurants/<id>/menu/ endpoint; menu items ride along inside
RestaurantDetailSerializer.menu_items, so we test through the
restaurant detail endpoint to mirror how the frontend consumes them.
"""

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from restaurants.models import MenuItem, Tag
from tests.factories import RestaurantFactory, UserFactory


@pytest.mark.critical
@pytest.mark.django_db
def test_menuitem_dietary_tag_surfaces_in_restaurant_detail():
	veg = Tag.objects.get(slug="vegetarian")
	rec = Tag.objects.get(slug="recommended")
	assert veg.kind == "dietary"
	assert rec.kind == "highlight"

	restaurant = RestaurantFactory()
	salad = MenuItem.objects.create(
		restaurant=restaurant,
		name="House Salad",
		price=10,
		category=MenuItem.Category.STARTER,
	)
	salad.tags.set([veg, rec])

	client = APIClient()
	client.force_authenticate(user=UserFactory())
	res = client.get(reverse("restaurant-detail", kwargs={"pk": restaurant.id}))
	assert res.status_code == 200, res.content

	body = res.json()
	items = body["menuItems"]
	rendered = next((i for i in items if i["name"] == "House Salad"), None)
	assert rendered is not None, items

	# Old surface is gone, new surface carries kind metadata.
	assert "isVegetarian" not in rendered
	assert "isGlutenFree" not in rendered
	assert "isRecommended" not in rendered

	rendered_tags = {t["slug"]: t["kind"] for t in rendered["tags"]}
	assert rendered_tags == {"vegetarian": "dietary", "recommended": "highlight"}


@pytest.mark.critical
@pytest.mark.django_db
def test_three_canonical_tags_are_seeded_with_correct_kind():
	"""Migration 0011 seeds the 3 tags backing the legacy booleans. Lock it
	in: any future migration that drops/renames these would break the
	dietary-badges UX."""
	canonicals = {
		t.slug: t.kind
		for t in Tag.objects.filter(slug__in=["vegetarian", "gluten-free", "recommended"])
	}
	assert canonicals == {
		"vegetarian": "dietary",
		"gluten-free": "dietary",
		"recommended": "highlight",
	}
