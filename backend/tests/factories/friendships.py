import factory

from accounts.models import EmailInvitation, Friendship
from tests.factories.base import BaseFactory
from tests.factories.users import UserFactory


class FriendshipFactory(BaseFactory):
	class Meta:
		model = Friendship

	from_user = factory.SubFactory(UserFactory)
	to_user = factory.SubFactory(UserFactory)
	status = Friendship.Status.PENDING


class EmailInvitationFactory(BaseFactory):
	class Meta:
		model = EmailInvitation

	from_user = factory.SubFactory(UserFactory)
	email = factory.Sequence(lambda n: f"invitee{n}@example.com")
	accepted = False
