"""Resuelve los imports que están esperando. Lo corre el cron, por minuto.

Mismo patrón que `dispatch_notifications`: la cola vive en Postgres y esto la
despacha. Matchear 200 filas contra Google no entra en el tiempo de un request,
y el usuario no tiene que quedarse mirando una pantalla mientras pasa.
"""

import logging

from django.core.management.base import BaseCommand

from imports.services.run import run_pending

logger = logging.getLogger(__name__)


class Command(BaseCommand):
	help = "Matchea los imports pendientes contra el catálogo y Google"

	def add_arguments(self, parser):
		parser.add_argument("--batch-size", type=int, default=5)

	def handle(self, *args, **options):
		stats = run_pending(batch_size=options["batch_size"])
		logger.info("run_pending_imports: %s", stats)
		self.stdout.write(
			f"jobs={stats['jobs']} filas={stats['filas']} liberados={stats['released']}"
		)
