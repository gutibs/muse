"""¿Sigue respondiendo Google?

Existe porque el 2026-09-08 la cuenta de billing de GCP estaba cerrada, Places
contestaba PERMISSION_DENIED y nadie se enteró: el corte se descubrió corriendo
la suite completa antes de un merge, de casualidad. Buscar y agregar un
restaurante es el flujo principal de la app, así que el silencio duró lo que
duró sin que nada lo delatara.

Tres piezas separadas a propósito, para poder probarlas de a una: `probe_places`
habla con Google, `update_state` habla con la base y decide si hay algo que
avisar, y `mark_alerted` cierra el aviso. Mandar el mail es del comando: este
módulo no sabe qué es un email.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import timedelta

from django.utils import timezone

from places.models import IntegrationHealth
from places.services import google_places as gp

logger = logging.getLogger(__name__)

GOOGLE_PLACES = "google_places"

# Una búsqueda cualquiera con resultados garantizados. Región Hong Kong porque
# es donde está el foco del producto, y el tipo restaurante porque es
# exactamente lo que pide la app: si esto anda, el flujo principal anda.
_PROBE_BODY = {
	"input": "sushi",
	"includedPrimaryTypes": ["restaurant"],
	"includedRegionCodes": ["hk"],
}


@dataclass(frozen=True)
class CheckResult:
	healthy: bool
	error: str = ""


@dataclass(frozen=True)
class Outcome:
	"""Qué quedó registrado y qué hay que hacer con eso."""

	state: IntegrationHealth
	should_alert: bool
	recovered: bool
	downtime: timedelta | None = None


def probe_places(*, retries: int = 1, pause: float = 5.0) -> CheckResult:
	"""Una llamada real a Places, con un reintento antes de declararlo caído.

	El reintento es contra el falso positivo: un timeout suelto no es un corte,
	y un mail que avisa de cortes que no pasaron se archiva sin leer. Sólo
	cuesta una llamada extra cuando la primera ya falló.

	Un 200 sin predicciones cuenta como sano. Cero resultados es un hecho sobre
	los datos de Google, no sobre si nos atiende; una key mal restringida o un
	proyecto sin billing no contestan 200, contestan 403.
	"""
	error = ""
	for intento in range(retries + 1):
		try:
			gp.autocomplete(_PROBE_BODY)
			return CheckResult(healthy=True)
		except gp.GooglePlacesError as exc:
			error = exc.detail or exc.message
			logger.warning(
				"Places health probe failed (intento %s/%s): %s", intento + 1, retries + 1, error
			)
			if intento < retries and pause:
				time.sleep(pause)
		except Exception as exc:
			# Un monitor que se cae con la excepción que no esperaba no es un
			# monitor: si esto sube, `update_state` no corre, no queda registro
			# de nada y el corte pasa igual de desapercibido que antes. Cualquier
			# fallo cuenta como caída, con el tipo en el mensaje para poder
			# distinguir "Google no atiende" de "nuestro parser explotó".
			error = f"{type(exc).__name__}: {exc}"
			logger.exception("Places health probe crashed (intento %s)", intento + 1)
			if intento < retries and pause:
				time.sleep(pause)

	return CheckResult(healthy=False, error=error)


def update_state(service: str, result: CheckResult) -> Outcome:
	"""Registra el chequeo y dice si hay que avisar.

	Se avisa en la transición, no en cada corrida: con el chequeo cada 6 horas,
	un corte de tres días son 2 mails y no 12.

	Un estado sin avisar sigue pendiente hasta que el aviso salga de verdad, así
	que si el mail falla el próximo chequeo lo reintenta.
	"""
	now = timezone.now()
	state, created = IntegrationHealth.objects.get_or_create(
		service=service,
		defaults={
			"is_healthy": result.healthy,
			"checked_at": now,
			"changed_at": now,
			"last_error": result.error,
			# La primera corrida sólo avisa si arranca rota: nadie quiere un
			# mail que diga que todo está bien.
			"alerted": result.healthy,
		},
	)
	if created:
		return Outcome(state=state, should_alert=not result.healthy, recovered=False)

	cambio = state.is_healthy != result.healthy

	state.checked_at = now
	state.last_error = result.error
	if cambio:
		if result.healthy:
			# Se calcula acá y se persiste porque un renglón más abajo
			# `changed_at` deja de ser el momento de la caída. Un aviso que hay
			# que reintentar seis horas después necesita este número.
			state.last_downtime = now - state.changed_at
		state.is_healthy = result.healthy
		state.changed_at = now
		state.alerted = False
	state.save(
		update_fields=[
			"checked_at",
			"last_error",
			"is_healthy",
			"changed_at",
			"alerted",
			"last_downtime",
		]
	)

	return Outcome(
		state=state,
		should_alert=not state.alerted,
		recovered=state.is_healthy,
		downtime=state.last_downtime if state.is_healthy else None,
	)


def mark_alerted(state: IntegrationHealth) -> None:
	"""El aviso salió. Recién acá el estado deja de estar pendiente."""
	state.alerted = True
	state.save(update_fields=["alerted"])
