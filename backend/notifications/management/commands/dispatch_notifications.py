"""Despacha la cola de notificaciones inmediatas.

Lo corre el cron. Procesa un lote por corrida y sale: si queda trabajo, lo
toma la corrida siguiente. Un comando que se queda dando vueltas se solaparía
con el próximo cron, y aunque `skip_locked` evita mandar dos veces, no evita
que se acumulen procesos.
"""

import logging

from django.core.management.base import BaseCommand

from notifications.services.dispatch import run_pending

logger = logging.getLogger(__name__)


class Command(BaseCommand):
	help = "Despacha las notificaciones push pendientes"

	def add_arguments(self, parser):
		parser.add_argument("--batch-size", type=int, default=50)

	def handle(self, *args, **options):
		batch = options["batch_size"]
		if batch < 1:
			self.stderr.write("--batch-size tiene que ser >= 1")
			return
		stats = run_pending(batch_size=batch)
		logger.info("dispatch_notifications: %s", stats)
		self.stdout.write(
			f"enviadas={stats['sent']} fallidas={stats['failed']} "
			f"descartadas={stats['discarded']} liberadas={stats['released']}"
		)
