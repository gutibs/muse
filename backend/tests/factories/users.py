import factory
from django.contrib.auth import get_user_model

from accounts.models import Profile
from tests.factories.base import BaseFactory

User = get_user_model()


class UserFactory(BaseFactory):
	"""Creates a real auth user. The Profile is created automatically by
	the post_save signal in accounts/signals.py — we don't manually create
	one here to avoid duplicating the FK."""

	class Meta:
		model = User
		django_get_or_create = ("username",)

	username = factory.Sequence(lambda n: f"user{n}")
	email = factory.LazyAttribute(lambda o: f"{o.username}@example.com")
	password = factory.PostGenerationMethodCall("set_password", "test-pass-123")


class ProfileFactory(BaseFactory):
	"""Use only to mutate the auto-created profile (e.g. set display_name).
	For a fresh user, prefer `UserFactory()` and edit `.profile` after."""

	class Meta:
		model = Profile
		django_get_or_create = ("user",)

	user = factory.SubFactory(UserFactory)
	display_name = factory.Faker("name")
