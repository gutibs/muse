"""Único punto de salida de una notificación.

`notify()` encola; nadie más escribe en `NotificationJob` y nadie llama a FCM
por su cuenta. Hoy despacha sólo push: los emails que ya existen siguen por
`accounts/services/email.py` hasta que la cola tenga rodaje.

La firma no menciona FCM a propósito — cuando entre iOS, el canal se elige
acá adentro y los llamadores no cambian.
"""

import logging
from datetime import timedelta

from django.db import IntegrityError, transaction
from django.utils import timezone as dj_timezone
from django.utils import translation

from notifications.models import DeviceToken, NotificationJob
from notifications.services import fcm

logger = logging.getLogger(__name__)

# Qué preferencia del perfil gobierna cada tipo. Un tipo sin entrada acá no se
# manda: preferimos no notificar antes que notificar algo que nadie eligió.
_PREFERENCE_BY_KIND = {
	NotificationJob.Kind.FRIENDSHIP_REQUEST: "notify_friend_request",
	NotificationJob.Kind.FRIENDSHIP_ACCEPTED: "notify_friend_accepted",
}

# Límites de FCM con margen. Un nombre largo cortado a la mitad de una palabra
# se ve peor que uno con elipsis: en el catálogo real hay cosas como "The
# Peppertree Restaurant - La Veranda Resort Phu Quoc MGallery".
TITLE_MAX = 65
BODY_MAX = 240


def truncate(text: str, limit: int) -> str:
	if len(text) <= limit:
		return text
	return text[: limit - 1].rstrip() + "…"


def wants(user, kind) -> bool:
	"""Si esta persona quiere recibir este tipo. Sin perfil, no se manda."""
	profile = getattr(user, "profile", None)
	if profile is None:
		return False
	field = _PREFERENCE_BY_KIND.get(kind)
	if field is None:
		return False
	return bool(getattr(profile, field, False))


def notify(
	*, recipient, kind, actor=None, context=None, idempotency_key: str
) -> NotificationJob | None:
	"""Encola una notificación inmediata. Devuelve None si no corresponde.

	Se llama desde signals con `transaction.on_commit`, así que cuando corre la
	fila ya está commiteada y no se encola nada por una transacción que después
	se revierte.
	"""
	if recipient is None or not recipient.is_active:
		return None
	if actor is not None and actor.pk == recipient.pk:
		# Nadie se notifica a sí mismo. Pasa con datos de prueba y sería
		# desconcertante en producción.
		return None
	if not wants(recipient, kind):
		return None

	try:
		with transaction.atomic():
			return NotificationJob.objects.create(
				recipient=recipient,
				actor=actor,
				kind=kind,
				context=context or {},
				idempotency_key=idempotency_key,
			)
	except IntegrityError:
		# Ya estaba encolado. Es el caso normal al restaurar un backup o al
		# reintentar una request, no un error.
		logger.info("notification already queued: %s", idempotency_key)
		return None


def tokens_for(user) -> list[DeviceToken]:
	return list(DeviceToken.objects.filter(user=user).order_by("-last_seen_at"))


def push_to_user(user, *, title: str, body: str, data: dict | None = None) -> int:
	"""Manda a todos los dispositivos de una persona. Devuelve cuántos aceptaron.

	Un token muerto se borra y no cuenta como fallo del envío: el resto sí se
	entregó. Que se caiga un teléfono viejo no puede hacer fallar el job.
	"""
	delivered = 0
	last_error = None

	for device in tokens_for(user):
		try:
			fcm.send(
				token=device.token,
				title=truncate(title, TITLE_MAX),
				body=truncate(body, BODY_MAX),
				data=data,
			)
			delivered += 1
		except fcm.FCMError as exc:
			if exc.dead_token:
				logger.info("dead token removed for user %s: %s", user.pk, exc.message)
				device.delete()
				continue
			last_error = exc
			logger.warning("push failed for user %s: %s", user.pk, exc.message)

	if delivered == 0 and last_error is not None:
		raise last_error
	return delivered


def user_language(user) -> str:
	profile = getattr(user, "profile", None)
	return getattr(profile, "language", None) or "en"


def render(job: NotificationJob) -> tuple[str, str]:
	"""Título y cuerpo, en el idioma del destinatario.

	El idioma sale del perfil y no de un header: el push lo inicia el servidor,
	así que no hay request del destinatario de donde leerlo.
	"""
	from django.utils.translation import gettext as _

	actor_name = job.context.get("actor_name") or _("Someone")

	with translation.override(user_language(job.recipient)):
		if job.kind == NotificationJob.Kind.FRIENDSHIP_REQUEST:
			return _("New friend request"), _("%(name)s wants to connect on Muse.") % {
				"name": actor_name
			}
		if job.kind == NotificationJob.Kind.FRIENDSHIP_ACCEPTED:
			return _("You are now friends"), _("%(name)s accepted your request.") % {
				"name": actor_name
			}
	raise ValueError(f"tipo de notificación sin texto: {job.kind}")


def _release_stale_locks() -> int:
	"""Devuelve a la cola los jobs que quedaron tomados por un proceso muerto.

	El deploy hace `down` + `up` en cada push: un despachador cortado a mitad
	de lote deja filas en `processing` que nadie va a tocar nunca más.
	"""
	cutoff = dj_timezone.now() - timedelta(minutes=NotificationJob.LOCK_TIMEOUT_MINUTES)
	return NotificationJob.objects.filter(
		state=NotificationJob.State.PROCESSING,
		locked_at__lt=cutoff,
	).update(state=NotificationJob.State.PENDING, locked_at=None)


def _claim(batch_size: int) -> list[NotificationJob]:
	"""Toma un lote. `skip_locked` evita que dos corridas manden lo mismo."""
	with transaction.atomic():
		jobs = list(
			NotificationJob.objects.select_for_update(skip_locked=True)
			.filter(state=NotificationJob.State.PENDING)
			.order_by("created_at")[:batch_size]
		)
		if jobs:
			NotificationJob.objects.filter(pk__in=[j.pk for j in jobs]).update(
				state=NotificationJob.State.PROCESSING,
				locked_at=dj_timezone.now(),
			)
	return jobs


def _is_stale(job: NotificationJob) -> bool:
	return job.created_at < dj_timezone.now() - timedelta(hours=NotificationJob.STALE_HOURS)


def run_pending(batch_size: int = 50) -> dict:
	"""Despacha un lote. Es lo que corre el cron.

	Cada job se revalida antes de mandarse: la preferencia pudo apagarse y la
	cuenta pudo borrarse entre el encolado y ahora.
	"""
	released = _release_stale_locks()
	stats = {"released": released, "sent": 0, "failed": 0, "discarded": 0}

	for job in _claim(batch_size):
		if _is_stale(job):
			job.state = NotificationJob.State.DISCARDED
			job.last_error = "stale"
			job.save(update_fields=["state", "last_error", "updated_at"])
			stats["discarded"] += 1
			continue

		if not wants(job.recipient, job.kind) or not job.recipient.is_active:
			job.state = NotificationJob.State.DISCARDED
			job.last_error = "recipient opted out or inactive"
			job.save(update_fields=["state", "last_error", "updated_at"])
			stats["discarded"] += 1
			continue

		title, body = render(job)
		job.attempts += 1
		try:
			push_to_user(
				job.recipient,
				title=title,
				body=body,
				data={
					"kind": job.kind,
					**{k: v for k, v in job.context.items() if k != "actor_name"},
				},
			)
		except fcm.FCMError as exc:
			job.last_error = exc.message[:500]
			over = job.attempts >= NotificationJob.MAX_ATTEMPTS
			job.state = NotificationJob.State.FAILED if over else NotificationJob.State.PENDING
			job.locked_at = None
			job.save(update_fields=["state", "attempts", "last_error", "locked_at", "updated_at"])
			stats["failed"] += 1
			continue

		job.state = NotificationJob.State.SENT
		job.locked_at = None
		job.save(update_fields=["state", "attempts", "locked_at", "updated_at"])
		stats["sent"] += 1

	return stats
