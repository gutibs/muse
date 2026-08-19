"""Borra los eventos crudos que pasaron la ventana de retención.

	python manage.py prune_analytics

Sin parámetros a propósito: la ventana es lo que declara la política de
privacidad, no una perilla de la operación. Consolida antes de borrar, y sólo
borra meses cerrados — ver `analytics/services/retention.py`.
"""

from django.core.management.base import BaseCommand

from analytics.services.retention import RETENTION, prune_events


class Command(BaseCommand):
	help = "Delete raw analytics events past the retention window, keeping the aggregates."

	def handle(self, *args, **options):
		deleted = prune_events()
		self.stdout.write(
			self.style.SUCCESS(
				f"Deleted {deleted} event(s) older than {RETENTION.days} days. "
				"Monthly aggregates were written first and are kept."
			)
		)
