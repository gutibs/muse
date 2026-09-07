"""Despacha los imports pendientes y confirma los que la persona eligió.

Tercera pieza del importador: junta el parseo con el matcheo. Corre desde el
cron, igual que `dispatch_notifications`, porque matchear 200 filas contra
Google no entra en el tiempo de un request.

**Nada crea un pin hasta que la persona confirma.** El match por nombre acierta
alto pero no perfecto, y un import a ciegas llena la cuenta de alguien con
restaurantes equivocados. `run_pending` deja el job en `ready` con su reporte;
`confirm_job` crea los pins de lo que se eligió.
"""

import logging
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from imports.models import ImportJob
from imports.services.match import MatchOutcome, match_row

logger = logging.getLogger(__name__)

# Lo que cuenta como "encontrado" para la persona: ya estaba, o lo trajimos.
EXITOSOS = {MatchOutcome.CATALOGUE, MatchOutcome.IMPORTED}


def run_pending(batch_size: int = 5) -> dict:
	"""Resuelve los jobs pendientes. Devuelve cuántos tocó."""
	liberados = _liberar_zombis()
	stats = {"jobs": 0, "filas": 0, "released": liberados}

	for job in _tomar(batch_size):
		try:
			_resolver(job)
			stats["jobs"] += 1
			stats["filas"] += job.total
		except Exception as exc:
			# Ancho a propósito: un job roto no puede dejar la cola trabada
			# para los demás, ni quedarse en `processing` para siempre.
			logger.exception("import %s falló entero: %s", job.pk, exc)
			job.state = ImportJob.State.FAILED
			job.locked_at = None
			job.save(update_fields=["state", "locked_at", "updated_at"])

	return stats


def _tomar(batch_size: int) -> list[ImportJob]:
	ahora = timezone.now()
	ids = list(
		ImportJob.objects.filter(state=ImportJob.State.PENDING).values_list("pk", flat=True)[
			:batch_size
		]
	)
	ImportJob.objects.filter(pk__in=ids).update(state=ImportJob.State.PROCESSING, locked_at=ahora)
	return list(ImportJob.objects.filter(pk__in=ids))


def _liberar_zombis() -> int:
	"""Devuelve a la cola lo que quedó tomado por un proceso muerto.

	El deploy hace `down` + `up` en cada push: un despachador cortado a mitad
	deja filas en `processing` que nadie volvería a tocar.
	"""
	corte = timezone.now() - timedelta(minutes=ImportJob.LOCK_TIMEOUT_MINUTES)
	return ImportJob.objects.filter(state=ImportJob.State.PROCESSING, locked_at__lt=corte).update(
		state=ImportJob.State.PENDING, locked_at=None
	)


def _resolver(job: ImportJob) -> None:
	reporte = []
	matched = failed = 0

	for fila in job.report:
		resultado = match_row(fila, job.user)
		entrada = {
			"row": fila.get("row"),
			"name": fila.get("name", ""),
			"city": fila.get("city", ""),
			"outcome": str(resultado.outcome),
			"restaurant_id": resultado.restaurant.pk if resultado.restaurant else None,
			"detail": resultado.detail,
		}
		if resultado.outcome in EXITOSOS:
			matched += 1
		else:
			failed += 1
		reporte.append(entrada)

	job.report = reporte
	job.processed = len(reporte)
	job.matched = matched
	job.failed = failed
	job.state = ImportJob.State.READY
	job.locked_at = None
	job.save()


@transaction.atomic
def confirm_job(job: ImportJob, restaurant_ids: list[int]) -> int:
	"""Crea los pins `to_visit` de lo que la persona eligió. Devuelve cuántos."""
	from pins.models import Pin

	if job.state != ImportJob.State.READY:
		# Confirmar dos veces duplicaría pins, y confirmar algo que todavía no
		# se matcheó crearía pins de filas sin resolver.
		return 0

	# **Los ids se cruzan contra el reporte, no se confían.** Vienen del
	# cliente: sin esto, cualquiera se pinea lo que quiera mandando ids que
	# nunca salieron de su archivo.
	permitidos = {
		fila["restaurant_id"] for fila in job.report if fila.get("restaurant_id") is not None
	}
	elegidos = permitidos & set(restaurant_ids)

	ya_pineados = set(
		Pin.objects.filter(user=job.user, restaurant_id__in=elegidos).values_list(
			"restaurant_id", flat=True
		)
	)

	nuevos = [
		Pin(user=job.user, restaurant_id=rid, status=Pin.Status.TO_VISIT)
		for rid in elegidos - ya_pineados
	]
	# `bulk_create` saltea `save()`, así que no corre `full_clean` ni dispara
	# los signals de Activity. Es deliberado: un import de 50 lugares no tiene
	# que llenar el feed de los amigos con 50 entradas. La validación que
	# importa —status ↔ rating— la cumple la construcción: `to_visit` sin
	# rating es siempre válido.
	Pin.objects.bulk_create(nuevos)

	job.state = ImportJob.State.CONFIRMED
	job.save(update_fields=["state", "updated_at"])

	logger.info("import %s confirmado: %s pins creados", job.pk, len(nuevos))
	return len(nuevos)
