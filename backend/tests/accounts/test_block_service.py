"""RF14 — las dos funciones sobre las que se apoya todo el bloqueo.

`blocked_user_ids` es el conjunto bidireccional que consumen las cinco
superficies; si cada una armara su propio Q, el bloqueo se olvidaría en alguna.
`visible_friend_ids` es el reemplazo de `friend_ids` con el bloqueo aplicado, y
tiene que conservar su semántica exacta: excluye al viewer.
"""

import pytest
from django.contrib.auth.models import AnonymousUser

from accounts.models import Block, Friendship
from accounts.services.friendships import friend_ids
from accounts.services.visibility import blocked_user_ids, visible_friend_ids
from tests.factories import UserFactory


def _befriend(a, b):
	Friendship.objects.create(from_user=a, to_user=b, status=Friendship.Status.ACCEPTED)


@pytest.mark.critical
@pytest.mark.django_db
def test_blocked_user_ids_is_bidirectional():
	"""No importa quién bloqueó a quién: los dos se dejan de ver."""
	a, b, c = UserFactory(), UserFactory(), UserFactory()
	Block.objects.create(blocker=a, blocked=b)
	Block.objects.create(blocker=c, blocked=a)

	assert blocked_user_ids(a) == {b.id, c.id}
	assert blocked_user_ids(b) == {a.id}
	assert blocked_user_ids(c) == {a.id}


@pytest.mark.critical
@pytest.mark.django_db
def test_blocked_user_ids_is_empty_without_blocks_and_for_anonymous():
	assert blocked_user_ids(UserFactory()) == set()
	assert blocked_user_ids(AnonymousUser()) == set()


@pytest.mark.critical
@pytest.mark.django_db
def test_visible_friend_ids_drops_blocked_friends():
	me, friend, blocked_friend = UserFactory(), UserFactory(), UserFactory()
	_befriend(me, friend)
	_befriend(me, blocked_friend)
	Block.objects.create(blocker=me, blocked=blocked_friend)

	assert visible_friend_ids(me) == {friend.id}


@pytest.mark.critical
@pytest.mark.django_db
def test_visible_friend_ids_excludes_the_viewer_like_friend_ids_does():
	"""La razón de que exista esta función y no se use `visible_user_ids`:
	esa incluye al viewer, y el feed dejaría de comportarse como hoy."""
	me, friend = UserFactory(), UserFactory()
	_befriend(me, friend)

	assert visible_friend_ids(me) == friend_ids(me)
	assert me.id not in visible_friend_ids(me)


@pytest.mark.critical
@pytest.mark.django_db
def test_visible_friend_ids_of_anonymous_is_empty():
	assert visible_friend_ids(AnonymousUser()) == set()


@pytest.mark.critical
@pytest.mark.django_db
def test_a_block_in_either_direction_hides_the_friend():
	"""Aunque la amistad se borra al bloquear (RF3), la función no puede
	depender de eso: si quedara una fila de amistad por cualquier camino
	—D-005 recreándola, una carrera— el bloqueo tiene que ganar igual."""
	me, other = UserFactory(), UserFactory()
	_befriend(me, other)
	Block.objects.create(blocker=other, blocked=me)

	assert visible_friend_ids(me) == set()
	assert visible_friend_ids(other) == set()


@pytest.mark.critical
@pytest.mark.django_db
def test_the_same_block_cannot_be_stored_twice():
	from django.db import IntegrityError

	a, b = UserFactory(), UserFactory()
	Block.objects.create(blocker=a, blocked=b)

	with pytest.raises(IntegrityError):
		Block.objects.create(blocker=a, blocked=b)


@pytest.mark.critical
@pytest.mark.django_db
def test_blocks_in_opposite_directions_are_two_different_rows():
	a, b = UserFactory(), UserFactory()
	Block.objects.create(blocker=a, blocked=b)
	Block.objects.create(blocker=b, blocked=a)

	assert Block.objects.count() == 2
