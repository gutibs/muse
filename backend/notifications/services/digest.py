"""El resumen diario de actividad de los amigos.

**No pasa por la cola, y no es una simplificación.** Se arma en el momento de
mandarlo porque guardarlo antes sería guardar una foto: un pin que pasó a
privado entre el armado y el envío se filtraría igual, y eso es el mismo
oráculo que F2.A cerró, entrando por la puerta de al lado.

Por eso el contenido sale de `visible_pins`, la misma función que usan las
pantallas. Si mañana cambia la política de visibilidad, el resumen la hereda
sin que nadie se acuerde de tocar este archivo.
"""

import logging
import zoneinfo
from datetime import timedelta

from django.db import IntegrityError, transaction
from django.utils import timezone as dj_timezone
from django.utils import translation

from accounts.services.friendships import friend_ids
from accounts.services.visibility import visible_pin_filter
from feed.models import Activity
from notifications.models import DigestLog
from notifications.services import fcm
from notifications.services.dispatch import push_to_user, user_language
from pins.models import Pin

logger = logging.getLogger(__name__)

# Los verbos que cuentan como "un amigo guardó algo". `UPDATED` queda afuera a
# propósito: corregir una reseña tres veces no le importa a nadie más.
_DIGEST_VERBS = (Activity.Verb.PINNED, Activity.Verb.RATED)

WINDOW_HOURS = 24


def _zone(profile) -> zoneinfo.ZoneInfo:
	try:
		return zoneinfo.ZoneInfo(profile.timezone or "UTC")
	except (zoneinfo.ZoneInfoNotFoundError, ValueError):
		# Una zona inválida no puede dejar a alguien sin resumen para siempre.
		logger.warning("timezone inválida en el perfil %s: %r", profile.pk, profile.timezone)
		return zoneinfo.ZoneInfo("UTC")


def is_due(profile, *, now=None) -> bool:
	"""Si a esta persona le toca el resumen en la hora local que corre ahora."""
	now = now or dj_timezone.now()
	local = now.astimezone(_zone(profile))
	return local.hour == profile.digest_hour


def local_date(profile, *, now=None):
	now = now or dj_timezone.now()
	return now.astimezone(_zone(profile)).date()


def collect(user, *, now=None) -> list[Activity]:
	"""La actividad visible de los amigos de `user` en las últimas 24 horas.

	Pasa por `visible_pins`, así que respeta el nivel de cada pin y el bloqueo
	—`friend_ids` ya excluye a quien te bloqueó—. Un pin que dejó de ser
	visible desde que ocurrió no aparece: se evalúa ahora, no cuando pasó.
	"""
	now = now or dj_timezone.now()
	friends = friend_ids(user)
	if not friends:
		return []

	# No se usa `visible_pins` porque filtra por un único dueño y acá hacen
	# falta los pins de todos los amigos a la vez. Lo que sí se reusa es
	# `visible_pin_filter`, que es donde vive la política: si mañana cambia,
	# el resumen la hereda sin tocar este archivo.
	visible = Pin.objects.filter(user_id__in=friends).filter(visible_pin_filter(user))

	return list(
		Activity.objects.filter(
			actor_id__in=friends,
			verb__in=_DIGEST_VERBS,
			created_at__gte=now - timedelta(hours=WINDOW_HOURS),
			pin__in=visible,
		)
		.select_related("actor", "actor__profile", "pin", "pin__restaurant")
		.order_by("-created_at")
	)


def render(user, activities: list[Activity]) -> tuple[str, str]:
	"""Título y cuerpo del resumen, en el idioma de quien lo recibe.

	Los plurales salen de `ngettext` y no de concatenar: "1 lugar nuevo" y "3
	lugares nuevos" no se arman pegando un número adelante de un sustantivo.
	"""
	from django.utils.translation import gettext as _
	from django.utils.translation import ngettext

	names = []
	for activity in activities:
		profile = getattr(activity.actor, "profile", None)
		name = (getattr(profile, "display_name", "") or "").strip()
		if name and name not in names:
			names.append(name)

	count = len(activities)
	with translation.override(user_language(user)):
		title = ngettext(
			"%(count)d new place from your friends",
			"%(count)d new places from your friends",
			count,
		) % {"count": count}

		if len(names) == 1:
			body = _("%(name)s saved somewhere new.") % {"name": names[0]}
		elif len(names) == 2:
			body = _("%(first)s and %(second)s saved new places.") % {
				"first": names[0],
				"second": names[1],
			}
		elif names:
			body = _("%(first)s, %(second)s and others saved new places.") % {
				"first": names[0],
				"second": names[1],
			}
		else:
			body = _("Your friends saved new places today.")

	return title, body


def send_for(user, *, now=None) -> bool:
	"""Arma y manda el resumen de `user`. Devuelve si se mandó algo.

	Escribir `DigestLog` **antes** de mandar es deliberado: si el envío falla a
	mitad, es preferible que alguien se quede sin el resumen de un día a que lo
	reciba dos veces porque la corrida siguiente lo volvió a intentar.
	"""
	now = now or dj_timezone.now()
	profile = getattr(user, "profile", None)
	if profile is None or not profile.notify_daily_digest:
		return False

	activities = collect(user, now=now)
	if not activities:
		# Sin resumen vacío. Una notificación que dice "no pasó nada" es la
		# forma más rápida de que la apaguen.
		return False

	try:
		# El `atomic` propio no es decorativo: un IntegrityError deja la
		# transacción en curso inutilizable, y sin este bloque cualquier
		# consulta posterior —la del llamador incluida— revienta con
		# TransactionManagementError en vez de seguir con la persona siguiente.
		with transaction.atomic():
			DigestLog.objects.create(
				user=user,
				local_date=local_date(profile, now=now),
				item_count=len(activities),
			)
	except IntegrityError:
		# Ya se mandó hoy. Dos corridas en la misma hora no mandan dos veces.
		return False

	title, body = render(user, activities)
	try:
		push_to_user(user, title=title, body=body, data={"kind": "friend_activity_digest"})
	except fcm.FCMError as exc:
		logger.warning("digest no entregado a %s: %s", user.pk, exc.message)
		return False

	logger.info("digest enviado a %s con %d items", user.pk, len(activities))
	return True
