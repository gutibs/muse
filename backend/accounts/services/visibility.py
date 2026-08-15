"""Who is allowed to see whose data.

Sibling of `friendships.py`, and deliberately separate from it.
`friendships` answers a question of fact — are these two users friends —
while this module answers a question of policy: given a viewer and the
owner of some data, is the viewer allowed to see it. Today the policy is
"friends only", so the two answers coincide. They stop coinciding the
moment per-pin visibility levels exist, and at that point this is the one
module that changes.

Before this existed the policy was inlined at every call site: two views
repeated the same `if not are_friends(...): raise PermissionDenied`, while
the feed and the restaurant serializer built their own id sets. That is
five places to keep in sync, which is why the visibility work in phase 2
is priced as one module and not as five edits.
"""

from rest_framework.exceptions import PermissionDenied

from accounts.services.friendships import are_friends, friend_ids


def can_view(viewer, owner) -> bool:
	"""True if `viewer` may see data owned by `owner`.

	Anonymous viewers see nothing: the public surfaces (share links, and
	later profile QR codes) go through their own serializers with their own
	token check, not through this.
	"""
	if not getattr(viewer, "is_authenticated", False):
		return False
	return are_friends(viewer, owner)


def require_can_view(viewer, owner) -> None:
	"""`can_view`, raising the 403 instead of returning False.

	The message is intentionally the same everywhere: a viewer who is not
	allowed to see someone's data should not learn anything from the
	difference between "not friends" and "no such user".
	"""
	if not can_view(viewer, owner):
		raise PermissionDenied("You are not friends with this user.")


def visible_user_ids(viewer) -> set[int]:
	"""Every user whose data `viewer` may see, including themselves.

	The counterpart of `can_view` for queryset filtering. Note the
	difference from `friend_ids`, which excludes the viewer: when you are
	filtering "data I am allowed to see", your own data is included, and
	forgetting that is how a feed ends up hiding your own activity.
	"""
	if not getattr(viewer, "is_authenticated", False):
		return set()
	return friend_ids(viewer) | {viewer.id}
