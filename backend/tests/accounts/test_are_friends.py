import pytest

from accounts.models import Friendship
from accounts.views import _are_friends
from tests.factories import FriendshipFactory, UserFactory


@pytest.mark.critical
@pytest.mark.django_db
def test_are_friends_symmetric_and_accepted_only():
	a = UserFactory()
	b = UserFactory()
	c = UserFactory()

	FriendshipFactory(from_user=a, to_user=b, status=Friendship.Status.ACCEPTED)
	FriendshipFactory(from_user=a, to_user=c, status=Friendship.Status.PENDING)

	assert _are_friends(a, b) is True
	assert _are_friends(b, a) is True, "friendship lookup must be symmetric"
	assert _are_friends(a, c) is False, "PENDING friendships must not count"
	assert _are_friends(b, c) is False, "no relation at all must be False"
