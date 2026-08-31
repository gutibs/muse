"""Shape of the `reviews` block in RestaurantDetailSerializer.

The author used to be assembled as a hand-written dict — the only place in
the backend that serialized a user without a serializer. Besides drifting
from every other endpoint (a field added to UserPublicSerializer never
reached here), it emitted `avatar.url`, a MEDIA_URL-relative path. Inside
Capacitor the page origin is capacitor://localhost, so a relative avatar
resolves against the app bundle and never loads.
"""

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from rest_framework.test import APIClient

from pins.models import Pin
from tests.factories import PinFactory, RestaurantFactory, UserFactory

# Smallest valid GIF; enough for ImageField to accept the upload.
_GIF = (
	b"GIF89a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xff\xff\xff!"
	b"\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;"
)


def _client(user):
	c = APIClient()
	c.force_authenticate(user=user)
	return c


@pytest.mark.django_db
def test_review_author_avatar_is_an_absolute_url(tmp_path, settings):
	settings.MEDIA_ROOT = str(tmp_path)
	author = UserFactory()
	author.profile.display_name = "Jane"
	author.profile.avatar = SimpleUploadedFile("a.gif", _GIF, content_type="image/gif")
	author.profile.save()

	restaurant = RestaurantFactory()
	PinFactory(
		user=author,
		restaurant=restaurant,
		status=Pin.Status.VISITED,
		rating=5,
		comment="Great",
	)

	resp = _client(UserFactory()).get(reverse("restaurant-detail", kwargs={"pk": restaurant.pk}))

	assert resp.status_code == 200, resp.content
	avatar = resp.json()["reviews"][0]["user"]["avatar"]
	assert avatar.startswith("http"), f"avatar must be absolute for Capacitor, got {avatar!r}"


@pytest.mark.django_db
def test_review_author_shape_matches_the_shared_user_serializer():
	"""Same keys as everywhere else a user is exposed, and never the email:
	reviews are public to non-friends by design (D-001)."""
	author = UserFactory()
	author.profile.display_name = "Jane"
	author.profile.city = "Hong Kong"
	author.profile.save()

	restaurant = RestaurantFactory()
	PinFactory(
		user=author,
		restaurant=restaurant,
		status=Pin.Status.VISITED,
		rating=4,
		comment="Good",
	)

	resp = _client(UserFactory()).get(reverse("restaurant-detail", kwargs={"pk": restaurant.pk}))

	user_block = resp.json()["reviews"][0]["user"]
	assert set(user_block) == {
		"id",
		"displayName",
		"avatar",
		"city",
		"isDeleted",
		"isVerifiedInsider",
	}
	assert user_block["displayName"] == "Jane"
	assert user_block["isDeleted"] is False
	assert "email" not in user_block
