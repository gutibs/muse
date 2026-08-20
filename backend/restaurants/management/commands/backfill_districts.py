"""Rellena `Restaurant.district` con lo que ya trae el payload de Google.

	python manage.py backfill_districts [--dry-run] [--limit N]

Va por management command y no por data migration porque hay red de por
medio: una migración que sale a internet 550 veces bloquea el deploy y, si
falla a la mitad, deja el esquema a medio aplicar.

No cuesta llamadas nuevas para los places ya cacheados —`get_details` pasa
por la caché de 30 días— pero sí para el resto, y el cap gratuito de Google
son 1.000 llamadas por mes. De ahí `--limit`, para poder hacerlo por tandas.
"""

import logging

from django.core.management.base import BaseCommand

from places.services.place_details import get_details
from restaurants.models import Restaurant
from restaurants.services.google_place_parser import FIELD_MASK, parse_place

logger = logging.getLogger(__name__)


class Command(BaseCommand):
	help = "Fill in Restaurant.district from the Google payload we already fetch."

	def add_arguments(self, parser):
		parser.add_argument(
			"--dry-run",
			action="store_true",
			help="Show what would change without writing anything.",
		)
		parser.add_argument(
			"--limit",
			type=int,
			default=0,
			help="Stop after N restaurants. 0 means no limit.",
		)

	def handle(self, *args, **options):
		pendientes = (
			Restaurant.objects.filter(district="")
			.exclude(google_place_id=None)
			.exclude(google_place_id="")
			.order_by("id")
		)
		if options["limit"]:
			pendientes = pendientes[: options["limit"]]

		actualizados = fallados = vacios = 0

		for restaurant in pendientes:
			try:
				payload = get_details(restaurant.google_place_id, FIELD_MASK)
				district = parse_place(payload)["district"]
			except Exception:
				# Un place borrado en Google o una respuesta rota no puede
				# cortar la corrida entera: se registra con su id y se sigue.
				fallados += 1
				logger.exception(
					"No se pudo resolver el distrito (restaurant_id=%s, place_id=%s)",
					restaurant.id,
					restaurant.google_place_id,
				)
				continue

			if not district:
				# Google no manda sublocality para todos los lugares. No es un
				# error: hay direcciones que no tienen barrio.
				vacios += 1
				continue

			actualizados += 1
			if options["dry_run"]:
				self.stdout.write(f"  {restaurant.name} → {district}")
				continue
			restaurant.district = district
			restaurant.save(update_fields=["district"])

		prefijo = "[dry-run] " if options["dry_run"] else ""
		self.stdout.write(
			self.style.SUCCESS(
				f"{prefijo}{actualizados} con distrito, {vacios} sin sublocality en Google, "
				f"{fallados} con error."
			)
		)
