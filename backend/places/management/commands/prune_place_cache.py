"""Borra las respuestas de Places que pasaron los 30 días.

Correr desde un cron/scheduler, semanal alcanza:

    python manage.py prune_place_cache

Sin parámetros a propósito: la ventana la fijan los Google Maps Platform
Terms, no la operación. Un `--days` acá sería una perilla para violarlos.
"""

from django.core.management.base import BaseCommand

from places.services.place_details import CACHE_TTL
from places.services.place_details import purge_expired as purge_details
from places.services.place_photos import purge_expired as purge_photos


class Command(BaseCommand):
	help = "Prune cached Google Places data older than the 30-day terms window."

	def handle(self, *args, **options):
		details = purge_details()
		# Las fotos se borran una por una a propósito: `queryset.delete()` no
		# toca el storage y dejaría los archivos ocupando el disco del EC2.
		photos = purge_photos()
		self.stdout.write(
			self.style.SUCCESS(
				f"Deleted {details} cached details and {photos} photos "
				f"older than {CACHE_TTL.days} days."
			)
		)
