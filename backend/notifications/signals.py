"""De dónde salen las notificaciones inmediatas.

Sólo dos: te llegó una solicitud de amistad, y te la aceptaron. La actividad de
los amigos NO pasa por acá — va al resumen diario, que se arma en
`services/digest.py`.

Todo se encola con `transaction.on_commit`: si la transacción se revierte, no
queda una notificación anunciando algo que no pasó.
"""

import logging

from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from accounts.models import Friendship
from notifications.models import NotificationJob
from notifications.services.dispatch import notify

logger = logging.getLogger(__name__)


def _display_name(user) -> str:
	profile = getattr(user, "profile", None)
	return (getattr(profile, "display_name", "") or "").strip()


@receiver(post_save, sender=Friendship)
def notify_friendship(sender, instance, created, **kwargs):
	"""Solicitud recibida al crearse; aceptación cuando pasa a ACCEPTED.

	La clave de idempotencia incluye el estado, así que la misma amistad puede
	generar los dos avisos —uno al pedir y otro al aceptar— pero ninguno dos
	veces, ni siquiera si alguien restaura un backup.
	"""
	if created and instance.status == Friendship.Status.ACCEPTED:
		# Una amistad que nace aceptada es la de una invitación por email:
		# `RegisterSerializer._consume_invitations` la crea así cuando la
		# persona invitada se registra. Sin esta rama no se notificaba a nadie
		# —ni "te llegó una solicitud" ni "te la aceptaron"—, justo en el
		# momento para el que la feature existe en ese flujo: quien invitó se
		# entera de que su invitado entró.
		transaction.on_commit(
			lambda: notify(
				recipient=instance.from_user,
				actor=instance.to_user,
				kind=NotificationJob.Kind.FRIENDSHIP_ACCEPTED,
				context={
					"actor_name": _display_name(instance.to_user),
					"actor_id": instance.to_user_id,
				},
				idempotency_key=f"friendship:{instance.pk}:accepted",
			)
		)
		return

	if created and instance.status == Friendship.Status.PENDING:
		transaction.on_commit(
			lambda: notify(
				recipient=instance.to_user,
				actor=instance.from_user,
				kind=NotificationJob.Kind.FRIENDSHIP_REQUEST,
				context={
					"actor_name": _display_name(instance.from_user),
					"actor_id": instance.from_user_id,
				},
				idempotency_key=f"friendship:{instance.pk}:request",
			)
		)
		return

	if not created and instance.status == Friendship.Status.ACCEPTED:
		# Le avisa a quien la mandó, no a quien aceptó: el que aceptó ya sabe.
		transaction.on_commit(
			lambda: notify(
				recipient=instance.from_user,
				actor=instance.to_user,
				kind=NotificationJob.Kind.FRIENDSHIP_ACCEPTED,
				context={
					"actor_name": _display_name(instance.to_user),
					"actor_id": instance.to_user_id,
				},
				idempotency_key=f"friendship:{instance.pk}:accepted",
			)
		)
