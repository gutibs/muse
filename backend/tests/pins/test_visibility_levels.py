"""F2.A — los tres niveles de visibilidad por pin.

Lo que fija este archivo es la política: `visible_pin_filter` es el único
lugar que decide si un viewer puede ver el pin de otro, y las seis
superficies que muestran pins ajenos la heredan en vez de tener su propia
idea. Las decisiones de producto que hay detrás están en
`docs/SPEC_F2A_PRIVACIDAD.md`.
"""

import pytest
from django.contrib.auth.models import AnonymousUser

from accounts.models import Block, Friendship
from accounts.services.visibility import public_pin_filter, visible_pin_filter
from pins.models import Pin
from tests.factories import FriendshipFactory, PinFactory, RestaurantFactory, UserFactory


def _befriend(a, b):
	return FriendshipFactory(from_user=a, to_user=b, status=Friendship.Status.ACCEPTED)


def _visible_to(viewer):
	return set(Pin.objects.filter(visible_pin_filter(viewer)).values_list("id", flat=True))


@pytest.mark.critical
@pytest.mark.django_db
def test_a_public_pin_is_visible_to_a_stranger():
	viewer, owner = UserFactory(), UserFactory()
	pin = PinFactory(user=owner, restaurant=RestaurantFactory(), visibility=Pin.Visibility.PUBLIC)

	assert pin.id in _visible_to(viewer)


@pytest.mark.critical
@pytest.mark.django_db
def test_the_owner_always_sees_their_own_private_pin():
	owner = UserFactory()
	pin = PinFactory(user=owner, restaurant=RestaurantFactory(), visibility=Pin.Visibility.PRIVATE)

	assert pin.id in _visible_to(owner)


@pytest.mark.critical
@pytest.mark.django_db
def test_a_friends_only_pin_is_visible_to_a_friend():
	viewer, owner = UserFactory(), UserFactory()
	_befriend(viewer, owner)
	pin = PinFactory(user=owner, restaurant=RestaurantFactory(), visibility=Pin.Visibility.FRIENDS)

	assert pin.id in _visible_to(viewer)


@pytest.mark.critical
@pytest.mark.django_db
def test_a_friends_only_pin_is_invisible_to_a_stranger():
	viewer, owner = UserFactory(), UserFactory()
	pin = PinFactory(user=owner, restaurant=RestaurantFactory(), visibility=Pin.Visibility.FRIENDS)

	assert pin.id not in _visible_to(viewer)


@pytest.mark.critical
@pytest.mark.django_db
def test_a_pin_without_a_level_follows_the_owners_default():
	"""`visibility` NULL significa "lo que diga mi perfil", que es lo que
	tienen los 211 pins que ya existen."""
	viewer, owner = UserFactory(), UserFactory()
	owner.profile.default_pin_visibility = Pin.Visibility.PUBLIC
	owner.profile.save()
	pin = PinFactory(user=owner, restaurant=RestaurantFactory(), visibility=None)

	assert pin.id in _visible_to(viewer)


@pytest.mark.critical
@pytest.mark.django_db
def test_a_private_default_hides_pins_that_never_chose_a_level():
	viewer, owner = UserFactory(), UserFactory()
	owner.profile.default_pin_visibility = Pin.Visibility.PRIVATE
	owner.profile.save()
	pin = PinFactory(user=owner, restaurant=RestaurantFactory(), visibility=None)

	assert pin.id not in _visible_to(viewer)


@pytest.mark.critical
@pytest.mark.django_db
def test_changing_the_default_does_not_override_a_pin_with_its_own_level():
	viewer, owner = UserFactory(), UserFactory()
	chosen = PinFactory(
		user=owner, restaurant=RestaurantFactory(), visibility=Pin.Visibility.PUBLIC
	)
	inherited = PinFactory(user=owner, restaurant=RestaurantFactory(), visibility=None)

	owner.profile.default_pin_visibility = Pin.Visibility.PRIVATE
	owner.profile.save()

	visible = _visible_to(viewer)
	assert chosen.id in visible
	assert inherited.id not in visible


@pytest.mark.critical
@pytest.mark.django_db
def test_a_block_hides_even_a_public_pin():
	"""El bloqueo gana sobre el nivel, en las dos direcciones. Si no,
	`get_reviews` tendría que seguir excluyendo bloqueados por su cuenta y
	la próxima superficie que use el filtro heredaría el bypass."""
	viewer, owner = UserFactory(), UserFactory()
	Block.objects.create(blocker=viewer, blocked=owner)
	pin = PinFactory(user=owner, restaurant=RestaurantFactory(), visibility=Pin.Visibility.PUBLIC)

	assert pin.id not in _visible_to(viewer)


@pytest.mark.critical
@pytest.mark.django_db
def test_a_block_hides_a_public_pin_in_the_other_direction_too():
	viewer, owner = UserFactory(), UserFactory()
	Block.objects.create(blocker=owner, blocked=viewer)
	pin = PinFactory(user=owner, restaurant=RestaurantFactory(), visibility=Pin.Visibility.PUBLIC)

	assert pin.id not in _visible_to(viewer)


@pytest.mark.critical
@pytest.mark.django_db
def test_an_anonymous_viewer_sees_nothing_through_the_authenticated_filter():
	"""Contrato del módulo: las superficies anónimas piden `public_pin_filter`
	a propósito. Si `visible_pin_filter` devolviera algo para un anónimo, una
	view que se olvide de exigir login mostraría pins sin que nadie lo note."""
	owner = UserFactory()
	PinFactory(user=owner, restaurant=RestaurantFactory(), visibility=Pin.Visibility.PUBLIC)

	assert _visible_to(AnonymousUser()) == set()


@pytest.mark.critical
@pytest.mark.django_db
def test_the_public_filter_keeps_only_public_pins():
	owner = UserFactory()
	public = PinFactory(
		user=owner, restaurant=RestaurantFactory(), visibility=Pin.Visibility.PUBLIC
	)
	friends = PinFactory(
		user=owner, restaurant=RestaurantFactory(), visibility=Pin.Visibility.FRIENDS
	)
	private = PinFactory(
		user=owner, restaurant=RestaurantFactory(), visibility=Pin.Visibility.PRIVATE
	)

	kept = set(Pin.objects.filter(public_pin_filter()).values_list("id", flat=True))

	assert kept == {public.id}
	assert friends.id not in kept and private.id not in kept
