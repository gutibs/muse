from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.consent import POLICY_VERSIONS
from accounts.models import ConsentRecord, EmailInvitation, Friendship, Profile
from feed.models import Activity
from tests.factories import EmailInvitationFactory, UserFactory

User = get_user_model()


@pytest.mark.critical
@pytest.mark.django_db
@patch("accounts.serializers.send_welcome_email")
def test_register_creates_profile_and_consumes_invitation(welcome):
	a = UserFactory()
	EmailInvitationFactory(from_user=a, email="b@example.com", accepted=False)

	client = APIClient()
	url = reverse("register")
	response = client.post(
		url,
		data={
			"email": "b@example.com",
			"password": "Sup3r-strong-pass!",
			"displayName": "Bee",
			"acceptPrivacy": True,
		},
		format="json",
	)

	assert response.status_code == 202, response.content

	b = User.objects.filter(email__iexact="b@example.com").first()
	assert b is not None
	# Profile is created via post_save signal in accounts/signals.py
	assert Profile.objects.filter(user=b).exists()

	invite = EmailInvitation.objects.get(email__iexact="b@example.com")
	assert invite.accepted is True

	# Friendship between A and B exists with status=ACCEPTED. The invite
	# email promises automatic friendship; registering via the invite is
	# the user's consent. See docs/PRODUCT_DECISIONS.md D-005. Bug fixed
	# in C-008; previously the status was PENDING (AUDIT_BUGS_FOUND.md #1).
	friendship = Friendship.objects.filter(
		Q(from_user=a, to_user=b) | Q(from_user=b, to_user=a)
	).first()
	assert friendship is not None
	assert friendship.from_user == a and friendship.to_user == b
	assert friendship.status == Friendship.Status.ACCEPTED

	# C-008b: friendships born ACCEPTED must produce 2 feed entries (one per
	# side). Before the signal-guard fix in C-008b, this count was 0 because
	# the guard only fired on the PENDING->ACCEPTED transition.
	friendship_acts = Activity.objects.filter(
		verb=Activity.Verb.FRIENDSHIP,
		actor__in=[a, b],
	)
	assert friendship_acts.count() == 2
	# Each side's row points at the other as target_user.
	assert friendship_acts.filter(actor=a, target_user=b).exists()
	assert friendship_acts.filter(actor=b, target_user=a).exists()

	# Active consent: one ConsentRecord per policy, stamped with the current
	# version. These rows are the legal proof the user accepted GDPR + PDPO.
	consents = ConsentRecord.objects.filter(user=b)
	assert consents.count() == 2
	assert {c.policy for c in consents} == {
		ConsentRecord.Policy.GDPR,
		ConsentRecord.Policy.PDPO,
	}
	for c in consents:
		assert c.policy_version == POLICY_VERSIONS[c.policy]


@pytest.mark.critical
@pytest.mark.django_db
@pytest.mark.parametrize(
	"consent",
	[
		{},  # missing
		{"acceptPrivacy": False},  # explicitly refused
	],
)
def test_register_requires_active_consent(consent):
	"""Registration is rejected unless the privacy flag is explicitly true.
	A missing or false flag → 400 and no user/consent rows are created."""
	client = APIClient()
	url = reverse("register")
	response = client.post(
		url,
		data={
			"email": "noconsent@example.com",
			"password": "Sup3r-strong-pass!",
			**consent,
		},
		format="json",
	)

	assert response.status_code == 400, response.content
	assert not User.objects.filter(email__iexact="noconsent@example.com").exists()
	assert ConsentRecord.objects.count() == 0


@pytest.mark.django_db
@patch("accounts.serializers.send_welcome_email")
def test_register_consent_records_capture_ip(welcome):
	"""The consenting client IP is persisted on each ConsentRecord (proof of
	the context in which consent was given)."""
	client = APIClient()
	url = reverse("register")
	response = client.post(
		url,
		data={
			"email": "ip@example.com",
			"password": "Sup3r-strong-pass!",
			"acceptPrivacy": True,
		},
		format="json",
		REMOTE_ADDR="203.0.113.7",
	)

	assert response.status_code == 202, response.content
	user = User.objects.get(email__iexact="ip@example.com")
	records = ConsentRecord.objects.filter(user=user)
	assert records.count() == 2
	assert all(r.ip_address == "203.0.113.7" for r in records)


@pytest.mark.critical
@pytest.mark.django_db
def test_friendship_accept_creates_activities():
	"""Manual accept (PENDING -> ACCEPTED via API) must still produce the
	pair of feed entries. Locks in the original signal behavior so the
	C-008b guard tightening doesn't accidentally regress it."""
	a = UserFactory()
	b = UserFactory()
	# A sends a request → starts as PENDING.
	friendship = Friendship.objects.create(from_user=a, to_user=b, status=Friendship.Status.PENDING)
	assert (
		Activity.objects.filter(verb=Activity.Verb.FRIENDSHIP, actor__in=[a, b]).count() == 0
	), "PENDING creation must not produce friendship activities"

	# B accepts — emulates FriendshipViewSet.partial_update which uses
	# update_fields=["status", "updated_at"].
	friendship.status = Friendship.Status.ACCEPTED
	friendship.save(update_fields=["status", "updated_at"])

	acts = Activity.objects.filter(verb=Activity.Verb.FRIENDSHIP, actor__in=[a, b])
	assert acts.count() == 2
	assert acts.filter(actor=a, target_user=b).exists()
	assert acts.filter(actor=b, target_user=a).exists()
