"""Bloquear y desbloquear personas.

Punto único de escritura del modelo `Block`. La lectura vive en
`visibility.py::blocked_user_ids`, que es lo que consultan las superficies.

Bloquear no es sólo crear una fila: corta la relación existente y borra su
rastro. Ver los RF1-RF8 de docs/SPEC_F2B_REPORTAR_BLOQUEAR.md.
"""

import logging

from django.db import transaction
from django.db.models import Q
from rest_framework.exceptions import ValidationError

from accounts.models import Block, Friendship
from feed.models import Activity

logger = logging.getLogger(__name__)


@transaction.atomic
def block_user(*, blocker, blocked) -> Block:
	"""Bloquea a `blocked` en nombre de `blocker`. Idempotente.

	`get_or_create` y no un `create` a secas: con `unique_together`, el segundo
	intento levantaría `IntegrityError` y DRF no lo traduce — sale 500. Es el
	mismo camino por el que pinear dos veces devolvía 500 en lugar de 409.
	"""
	if blocker.pk == blocked.pk:
		# `are_friends(a, a)` devuelve True sin tocar la base, así que un
		# self-block dejaría al usuario sin ver sus propios datos.
		raise ValidationError({"user_id": ["You cannot block yourself."]})

	block, _created = Block.objects.get_or_create(blocker=blocker, blocked=blocked)
	_sever_relationship(blocker, blocked)
	logger.info("User blocked", extra={"blocker_id": blocker.pk, "blocked_id": blocked.pk})
	return block


@transaction.atomic
def unblock_user(*, blocker, blocked) -> None:
	"""Quita el bloqueo. NO revive la amistad (RF4): para volver a serlo hace
	falta una solicitud nueva."""
	Block.objects.filter(blocker=blocker, blocked=blocked).delete()
	logger.info("User unblocked", extra={"blocker_id": blocker.pk, "blocked_id": blocked.pk})


def _sever_relationship(a, b) -> None:
	"""Borra la amistad entre `a` y `b` en cualquier estado, y las actividades
	que la anunciaron.

	Las `Activity(FRIENDSHIP)` no se van solas: las crea un signal en
	`accounts/signals.py` y no hay ninguno que las borre — sólo
	`anonymise_user` las limpia a mano. Sin esto, un tercero amigo de los dos
	seguiría viendo en su feed una amistad que ya no existe, y filtrarla por
	bloqueo no alcanza: ese tercero no tiene bloqueo con ninguno.
	"""
	Friendship.objects.filter(Q(from_user=a, to_user=b) | Q(from_user=b, to_user=a)).delete()
	Activity.objects.filter(
		Q(actor=a, target_user=b) | Q(actor=b, target_user=a),
		verb=Activity.Verb.FRIENDSHIP,
	).delete()


def is_blocked(a, b) -> bool:
	"""True si hay bloqueo entre `a` y `b`, en cualquier dirección."""
	return Block.objects.filter(Q(blocker=a, blocked=b) | Q(blocker=b, blocked=a)).exists()
