"""accounts.services.friendships — canonical definition of "friends".

Covers friend_ids(), which did not exist as a shared helper: feed/views.py
and restaurants/serializers.py each carried an identical private copy. The
symmetry/ACCEPTED-only rules of are_friends() stay covered by
test_are_friends.py.
"""

import pytest
from django.contrib.auth.models import AnonymousUser

from accounts.models import Friendship
from accounts.services.friendships import friend_ids
from tests.factories import FriendshipFactory, UserFactory


@pytest.mark.critical
@pytest.mark.django_db
def test_friend_ids_is_symmetric_and_accepted_only():
	me = UserFactory()
	sent_to = UserFactory()
	received_from = UserFactory()
	pending = UserFactory()
	declined = UserFactory()
	stranger = UserFactory()

	FriendshipFactory(from_user=me, to_user=sent_to, status=Friendship.Status.ACCEPTED)
	FriendshipFactory(from_user=received_from, to_user=me, status=Friendship.Status.ACCEPTED)
	FriendshipFactory(from_user=me, to_user=pending, status=Friendship.Status.PENDING)
	FriendshipFactory(from_user=declined, to_user=me, status=Friendship.Status.DECLINED)
	FriendshipFactory(from_user=stranger, to_user=UserFactory(), status=Friendship.Status.ACCEPTED)

	ids = friend_ids(me)

	assert ids == {sent_to.id, received_from.id}, "direction must not matter"
	assert pending.id not in ids
	assert declined.id not in ids
	assert stranger.id not in ids


@pytest.mark.django_db
def test_friend_ids_excludes_self_and_handles_no_friends():
	loner = UserFactory()
	assert friend_ids(loner) == set()

	friend = UserFactory()
	FriendshipFactory(from_user=loner, to_user=friend, status=Friendship.Status.ACCEPTED)
	assert loner.id not in friend_ids(loner)


@pytest.mark.django_db
def test_friend_ids_of_anonymous_user_is_empty():
	"""Public surfaces (shared lists) serialize for unauthenticated callers."""
	assert friend_ids(AnonymousUser()) == set()
