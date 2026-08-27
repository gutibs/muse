"""Alta de denuncias.

Punto único de escritura de `Report`. La resolución se hace desde el admin de
Django: no hay pantalla de moderación propia, y para el volumen del beta el
admin alcanza.
"""

import logging

from django.db import transaction
from rest_framework.exceptions import ValidationError

from accounts.models import Report
from accounts.services.email import EmailSendError, send_report_notification_email

logger = logging.getLogger(__name__)


def create_report(*, reporter, reported_user, pin=None, reason: str, detail: str = "") -> Report:
	"""Crea la denuncia y avisa a un humano.

	El aviso va **fuera** de la transacción y su fallo no se propaga: perder la
	denuncia porque Resend está caído es peor que no avisar por mail. Queda la
	fila con status pendiente, que es lo que se mira en el admin.
	"""
	if reporter.pk == reported_user.pk:
		raise ValidationError({"reported_user_id": ["You cannot report yourself."]})

	if pin is not None and pin.user_id != reported_user.pk:
		raise ValidationError({"pin_id": ["That review does not belong to the reported user."]})

	with transaction.atomic():
		report = Report.objects.create(
			reporter=reporter,
			reported_user=reported_user,
			pin=pin,
			reason=reason,
			detail=detail,
			# Copia de lo denunciado: el comentario es editable y el reporte se
			# quedaría sin objeto si el autor lo cambia antes de la revisión.
			reported_comment=pin.comment if pin else "",
			reported_rating=pin.rating if pin else None,
		)

	try:
		send_report_notification_email(report=report)
	except EmailSendError as exc:
		logger.error(
			"Report notification not sent (status=%s): %s",
			exc.status_code,
			exc.message,
			extra={"report_id": report.pk},
		)

	logger.info(
		"Report created",
		extra={
			"report_id": report.pk,
			"reporter_id": reporter.pk,
			"reported_user_id": reported_user.pk,
			"reason": reason,
		},
	)
	return report
