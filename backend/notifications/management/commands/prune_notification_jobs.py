"""Limpieza de la cola y de los dispositivos muertos.

Va con el resto del mantenimiento semanal. Borra sólo lo terminado: un job
`pending` no se toca por viejo que sea — para eso está el descarte por
antigüedad del despachador, que además deja el motivo.
"""

import logging
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from notifications.models import DeviceToken, DigestLog, NotificationJob

logger = logging.getLogger(__name__)

TERMINAL = (
	NotificationJob.State.SENT,
	NotificationJob.State.FAILED,
	NotificationJob.State.DISCARDED,
)


class Command(BaseCommand):
	help = "Borra jobs terminados, marcas de resumen viejas y tokens sin uso"

	def handle(self, *args, **options):
		now = timezone.now()

		jobs, _ = NotificationJob.objects.filter(
			state__in=TERMINAL,
			updated_at__lt=now - timedelta(days=NotificationJob.KEEP_DAYS),
		).delete()

		logs, _ = DigestLog.objects.filter(
			local_date__lt=(now - timedelta(days=DigestLog.KEEP_DAYS)).date()
		).delete()

		tokens, _ = DeviceToken.objects.filter(
			last_seen_at__lt=now - timedelta(days=DeviceToken.STALE_DAYS)
		).delete()

		logger.info("prune_notification_jobs: jobs=%d digest_logs=%d tokens=%d", jobs, logs, tokens)
		self.stdout.write(f"jobs={jobs} digest_logs={logs} tokens={tokens}")
