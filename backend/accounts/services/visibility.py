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

from django.db.models import Q
from rest_framework.exceptions import PermissionDenied

from accounts.models import Block
from accounts.services.friendships import are_friends, friend_ids
from pins.constants import Visibility


def visible_pin_filter(viewer, prefix: str = "") -> Q:
	"""Los pins que `viewer` puede ver, como `Q` reutilizable.

	`prefix` permite aplicarlo desde otro modelo — el feed lo usa con
	`"pin__"` para filtrar Activities por el pin que cuelga de ellas.
	"""
	if not getattr(viewer, "is_authenticated", False):
		# Mismo contrato que `can_view`: por acá no ve nada nadie sin sesión.
		# Las superficies anónimas piden `public_pin_filter` explícitamente.
		return Q(pk__in=[])

	blocked = blocked_user_ids(viewer)
	own = Q(**{f"{prefix}user_id": viewer.id})
	# El bloqueo gana sobre el nivel, igual que gana sobre la amistad en
	# `can_view`. `visible_friend_ids` ya lo resta del lado de los amigos; acá
	# hace falta para los públicos, que no pasan por ninguna relación.
	unblocked = ~Q(**{f"{prefix}user_id__in": blocked})
	public = _pins_at_level(Visibility.PUBLIC, prefix) & unblocked
	friends = _pins_at_level(Visibility.FRIENDS, prefix) & Q(
		**{f"{prefix}user_id__in": friend_ids(viewer) - blocked}
	)
	return own | public | friends


def public_pin_filter(prefix: str = "") -> Q:
	"""Los pins que puede ver alguien sin sesión: sólo los públicos.

	Es lo que corresponde a un link compartido, que responde a cualquiera que
	lo tenga. Un pin `friends` no entra —el visitante del link es un
	desconocido— y uno `private` tampoco, ni siquiera si su dueño lo eligió a
	mano para una lista curada (decisión 3 del spec).
	"""
	return _pins_at_level(Visibility.PUBLIC, prefix)


def _pins_at_level(level, prefix: str = "") -> Q:
	"""Pins cuya visibilidad **efectiva** es `level`.

	Efectiva porque `Pin.visibility` NULL no es un valor sino una remisión:
	significa "lo que diga el default de mi perfil". Sin esta segunda rama,
	los pins que ya existen —todos con NULL— no serían de ningún nivel y
	desaparecerían de todas las superficies a la vez.
	"""
	return Q(**{f"{prefix}visibility": level}) | (
		Q(**{f"{prefix}visibility__isnull": True})
		& Q(**{f"{prefix}user__profile__default_pin_visibility": level})
	)


def can_view(viewer, owner) -> bool:
	"""True if `viewer` may see data owned by `owner`.

	Anonymous viewers see nothing: the public surfaces (share links, and
	later profile QR codes) go through their own serializers with their own
	token check, not through this.
	"""
	if not getattr(viewer, "is_authenticated", False):
		return False
	# El bloqueo gana sobre la amistad. No alcanza con que bloquear la borre
	# (RF3): si sobreviviera por cualquier camino —D-005 recreándola al
	# registrarse con un email invitado, una carrera— el perfil se seguiría
	# viendo con un bloqueo puesto.
	if owner.pk in blocked_user_ids(viewer):
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
	# Resta el bloqueo igual que `visible_friend_ids`. Hoy no la llama nadie en
	# producción, pero se llama "todos los usuarios cuyos datos puedo ver": la
	# próxima superficie que la tome heredaría un bypass del bloqueo y ningún
	# test se quejaría.
	return (friend_ids(viewer) - blocked_user_ids(viewer)) | {viewer.id}


def blocked_user_ids(viewer) -> set[int]:
	"""Ids con los que `viewer` tiene un bloqueo, en cualquier dirección.

	Es el único lugar donde se mira el modelo `Block`. Que sea uno solo es el
	punto: si cada superficie armara su propio `Q(blocker=…) | Q(blocked=…)`,
	alguna se olvidaría de una de las dos direcciones y el bloqueo sería
	asimétrico sin que nadie lo note.
	"""
	if not getattr(viewer, "is_authenticated", False):
		return set()

	rows = Block.objects.filter(Q(blocker=viewer) | Q(blocked=viewer)).values_list(
		"blocker_id", "blocked_id"
	)
	return {blocker if blocked == viewer.id else blocked for blocker, blocked in rows}


def visible_friend_ids(viewer) -> set[int]:
	"""Amigos de `viewer` sin los bloqueados. **Excluye al viewer**, igual que
	`friend_ids`.

	Es el reemplazo directo de `friend_ids` en las superficies que filtran
	"datos de mis amigos": el feed y los agregados del restaurante. No usar
	`visible_user_ids` para eso — incluye al viewer, y el feed pasaría a
	mostrar la actividad propia (ver el docstring de esa función).
	"""
	return friend_ids(viewer) - blocked_user_ids(viewer)


def visible_friend_and_blocked_ids(viewer) -> tuple[set[int], set[int]]:
	"""`(amigos visibles, bloqueados)` con una sola consulta de bloqueos.

	El feed necesita las dos cosas —a quién mostrar y a quién excluir como
	`target_user`— y pedirlas por separado corría la misma query dos veces.
	"""
	blocked = blocked_user_ids(viewer)
	return friend_ids(viewer) - blocked, blocked
