"""Borra las respuestas de Places que pasaron los 30 días.

Correr desde un cron/scheduler, semanal alcanza:

    python manage.py prune_place_cache

Sin parámetros a propósito: la ventana la fijan los Google Maps Platform
Terms, no la operación. Un `--days` acá sería una perilla para violarlos.
"""

from django.core.management.base import BaseCommand

from places.services.place_details import CACHE_TTL, purge_expired


class Command(BaseCommand):
	help = "Prune cached Google Places details older than the 30-day terms window."

	def handle(self, *args, **options):
		deleted = purge_expired()
		self.stdout.write(
			self.style.SUCCESS(f"Deleted {deleted} cached places older than {CACHE_TTL.days} days.")
		)
