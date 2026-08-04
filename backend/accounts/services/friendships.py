"""Friendship queries — the single place that knows how "friends" is defined.

A friendship is symmetric (either direction counts) and only ACCEPTED rows
count; PENDING and DECLINED never do. Encoding that in one module keeps a new
"friends only" filter from quietly shipping with half the rule.

`are_friends` used to live as `_are_friends` in accounts/views.py — the
underscore made it look private while three modules needed it. `friend_ids`
did not exist, so feed/views.py and restaurants/serializers.py each grew
their own identical copy of the same query and set-flattening loop.
"""

from django.db.models import Q

from accounts.models import Friendship


def are_friends(user_a, user_b) -> bool:
	"""True if the two users have an ACCEPTED friendship, in either direction.

	A user is trivially "friends" with themselves: callers use this to gate
	access to someone's data, and your own data is always yours.
	"""
	if user_a == user_b:
		return True
	return Friendship.objects.filter(
		(Q(from_user=user_a, to_user=user_b) | Q(from_user=user_b, to_user=user_a)),
		status=Friendship.Status.ACCEPTED,
	).exists()


def friend_ids(user) -> set[int]:
	"""IDs of everyone `user` is ACCEPTED friends with, excluding themselves.

	Returns an empty set for an anonymous user so callers can treat "not
	logged in" and "no friends yet" the same way.
	"""
	if not getattr(user, "is_authenticated", False):
		return set()

	pairs = Friendship.objects.filter(
		Q(from_user=user) | Q(to_user=user),
		status=Friendship.Status.ACCEPTED,
	).values_list("from_user_id", "to_user_id")

	ids: set[int] = set()
	for from_id, to_id in pairs:
		ids.add(from_id)
		ids.add(to_id)
	ids.discard(user.id)
	return ids
