"""Account deletion (GDPR art. 17 / PDPO right to erasure).

Product decision D-009: deletion ANONYMISES the account instead of dropping
the row. Pins, ratings and comments survive without an identity attached —
per D-001 public reviews are the value proposition, so a hard delete would
empty out every restaurant page the person ever reviewed. Everything that is
social or personal (friendships, invitations, feed activity, shared lists,
consent records, profile fields, avatar) is deleted outright.
"""

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.models import ConsentRecord, EmailInvitation, Friendship
from feed.models import Activity
from pins.models import Pin, SharedList
from tests.factories import (
	EmailInvitationFactory,
	FriendshipFactory,
	PinFactory,
	RestaurantFactory,
	SharedListFactory,
	UserFactory,
)

User = get_user_model()

PASSWORD = "test-pass-123"


def _auth_client(user):
	client = APIClient()
	client.force_authenticate(user=user)
	return client


@pytest.mark.critical
@pytest.mark.django_db
def test_delete_account_requires_authentication():
	"""An anonymous caller can never trigger erasure."""
	resp = APIClient().delete(reverse("profile"), {"currentPassword": PASSWORD}, format="json")
	assert resp.status_code == 401


@pytest.mark.critical
@pytest.mark.django_db
def test_delete_account_requires_correct_password():
	"""A stolen access token alone must not be enough to erase an account:
	the caller has to re-prove knowledge of the password."""
	user = UserFactory()
	client = _auth_client(user)

	missing = client.delete(reverse("profile"), {}, format="json")
	assert missing.status_code == 400

	wrong = client.delete(reverse("profile"), {"currentPassword": "not-my-password"}, format="json")
	assert wrong.status_code == 400

	user.refresh_from_db()
	assert user.is_active is True
	assert user.email and not user.email.endswith("@muse.local")


@pytest.mark.critical
@pytest.mark.django_db
def test_delete_account_anonymises_identity_but_keeps_reviews():
	"""The identity is scrubbed; the review content stays readable."""
	user = UserFactory()
	user.profile.display_name = "Jane Doe"
	user.profile.bio = "I like noodles"
	user.profile.city = "Hong Kong"
	user.profile.phone = "+852 1234 5678"
	user.profile.instagram = "janedoe"
	user.profile.website = "https://jane.example"
	user.profile.save()

	restaurant = RestaurantFactory()
	pin = PinFactory(
		user=user,
		restaurant=restaurant,
		status=Pin.Status.VISITED,
		rating=5,
		comment="Best dumplings in town",
	)
	original_email = user.email

	resp = _auth_client(user).delete(
		reverse("profile"), {"currentPassword": PASSWORD}, format="json"
	)
	assert resp.status_code == 204, resp.content

	user.refresh_from_db()
	assert user.is_active is False
	assert user.email.startswith("deleted-") and user.email.endswith("@muse.local")
	assert user.username == user.email
	assert original_email not in (user.email, user.username)
	assert not user.has_usable_password()

	profile = user.profile
	profile.refresh_from_db()
	assert profile.deleted_at is not None
	assert profile.display_name == ""
	assert profile.bio == ""
	assert profile.city == ""
	assert profile.phone == ""
	assert profile.instagram == ""
	assert profile.website == ""
	assert not profile.avatar

	# The review survives, intact and still attached to the restaurant.
	pin.refresh_from_db()
	assert pin.comment == "Best dumplings in town"
	assert pin.rating == 5
	assert Pin.objects.filter(restaurant=restaurant).count() == 1


@pytest.mark.critical
@pytest.mark.django_db
def test_delete_account_wipes_social_graph_and_consent():
	"""Everything relational or personal goes: friendships in both directions,
	invitations sent and received, feed activity, shared links, consent rows."""
	user = UserFactory()
	friend = UserFactory()
	other = UserFactory()

	FriendshipFactory(from_user=user, to_user=friend, status=Friendship.Status.ACCEPTED)
	FriendshipFactory(from_user=other, to_user=user, status=Friendship.Status.PENDING)
	EmailInvitationFactory(from_user=user, email="invitee@example.com")
	EmailInvitationFactory(from_user=other, email=user.email)
	SharedListFactory(user=user)
	PinFactory(user=user)  # creates a feed Activity via signal
	ConsentRecord.objects.create(user=user, policy=ConsentRecord.Policy.GDPR, policy_version="x")

	assert Activity.objects.filter(actor=user).exists()

	resp = _auth_client(user).delete(
		reverse("profile"), {"currentPassword": PASSWORD}, format="json"
	)
	assert resp.status_code == 204, resp.content

	assert not Friendship.objects.filter(from_user=user).exists()
	assert not Friendship.objects.filter(to_user=user).exists()
	assert not EmailInvitation.objects.filter(from_user=user).exists()
	assert not EmailInvitation.objects.filter(email__iexact=user.email).exists()
	assert not SharedList.objects.filter(user=user).exists()
	assert not Activity.objects.filter(actor=user).exists()
	assert not Activity.objects.filter(target_user=user).exists()
	assert not ConsentRecord.objects.filter(user=user).exists()


@pytest.mark.critical
@pytest.mark.django_db
def test_deleted_account_cannot_authenticate_afterwards():
	"""is_active=False makes every outstanding JWT useless immediately."""
	user = UserFactory()
	client = APIClient()
	token = client.post(
		reverse("token_obtain"),
		{"username": user.username, "password": PASSWORD},
		format="json",
	)
	assert token.status_code == 200, token.content
	access = token.json()["access"]

	deleted = _auth_client(user).delete(
		reverse("profile"), {"currentPassword": PASSWORD}, format="json"
	)
	assert deleted.status_code == 204

	client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
	assert client.get(reverse("profile")).status_code == 401


@pytest.mark.django_db
def test_reviews_of_deleted_user_are_flagged_anonymous():
	"""The restaurant page must be able to render 'Anonymous' in the reader's
	own language, so the API exposes a flag rather than a hardcoded label."""
	author = UserFactory()
	author.profile.display_name = "Jane Doe"
	author.profile.save()
	reader = UserFactory()
	restaurant = RestaurantFactory()
	PinFactory(
		user=author,
		restaurant=restaurant,
		status=Pin.Status.VISITED,
		rating=4,
		comment="Solid ramen",
	)

	_auth_client(author).delete(reverse("profile"), {"currentPassword": PASSWORD}, format="json")

	resp = _auth_client(reader).get(reverse("restaurant-detail", kwargs={"pk": restaurant.pk}))
	assert resp.status_code == 200, resp.content
	reviews = resp.json()["reviews"]
	assert len(reviews) == 1
	assert reviews[0]["comment"] == "Solid ramen"
	assert reviews[0]["user"]["isDeleted"] is True
	assert reviews[0]["user"]["displayName"] == ""
