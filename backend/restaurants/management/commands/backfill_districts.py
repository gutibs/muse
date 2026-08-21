"""Rellena, desde el payload de Google que ya pedimos, lo que las filas viejas
no tienen: el distrito y los atributos del local.

	python manage.py backfill_districts [--dry-run] [--limit N] [--attributes]

Va por management command y no por data migration porque hay red de por
medio: una migración que sale a internet cientos de veces bloquea el deploy
y, si falla a la mitad, deja el esquema a medio aplicar.

Los dos datos salen de la misma respuesta, así que se resuelven juntos: pedir
el payload para el distrito y no aprovechar los atributos dejaría la
autoselección sin efecto sobre todo lo que ya está en el catálogo. Por
default sólo se visitan los que no tienen distrito; con `--attributes` se
recorre todo el catálogo con place_id, para las filas que ya quedaron
ubicadas antes de que existieran los atributos.

No cuesta llamadas nuevas para los places ya cacheados —`get_details` pasa
por la caché de 30 días— pero sí para el resto, y el cap gratuito de Google
son 1.000 llamadas por mes. De ahí `--limit`, para poder hacerlo por tandas.
"""

import logging

from django.core.management.base import BaseCommand

from places.services.place_details import get_details
from restaurants.models import Restaurant, Tag
from restaurants.services.google_place_parser import (
	FIELD_MASK,
	inferred_tag_slugs,
	parse_place,
)

logger = logging.getLogger(__name__)


class Command(BaseCommand):
	help = "Fill in district and venue attributes from the Google payload we already fetch."

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
		parser.add_argument(
			"--attributes",
			action="store_true",
			help="Visit every restaurant with a place_id, not only those missing a district.",
		)

	def handle(self, *args, **options):
		pendientes = (
			Restaurant.objects.exclude(google_place_id=None)
			.exclude(google_place_id="")
			.order_by("id")
		)
		if not options["attributes"]:
			pendientes = pendientes.filter(district="")
		if options["limit"]:
			pendientes = pendientes[: options["limit"]]

		ubicados = etiquetados = fallados = vacios = 0

		for restaurant in pendientes:
			try:
				payload = get_details(restaurant.google_place_id, FIELD_MASK)
				parsed = parse_place(payload)
			except Exception:
				# Un place borrado en Google o una respuesta rota no puede
				# cortar la corrida entera: se registra con su id y se sigue.
				fallados += 1
				logger.exception(
					"No se pudo leer el place (restaurant_id=%s, place_id=%s)",
					restaurant.id,
					restaurant.google_place_id,
				)
				continue

			district = parsed["district"]
			slugs = inferred_tag_slugs(payload)

			if district and not restaurant.district:
				ubicados += 1
				if not options["dry_run"]:
					restaurant.district = district
					restaurant.save(update_fields=["district"])
			elif not district and not restaurant.district:
				# Google no manda sublocality para todos los lugares. No es un
				# error: hay direcciones que no tienen barrio.
				vacios += 1

			if slugs:
				tags = list(Tag.objects.filter(slug__in=slugs))
				nuevos = [tag for tag in tags if tag not in restaurant.tags.all()]
				if nuevos:
					etiquetados += len(nuevos)
					if not options["dry_run"]:
						# Sólo se agrega: nunca se quita una etiqueta puesta a
						# mano desde el admin.
						restaurant.tags.add(*nuevos)

			if options["dry_run"] and (district or slugs):
				detalle = ", ".join(sorted(slugs)) or "sin atributos"
				self.stdout.write(f"  {restaurant.name} → {district or '—'} · {detalle}")

		prefijo = "[dry-run] " if options["dry_run"] else ""
		self.stdout.write(
			self.style.SUCCESS(
				f"{prefijo}{ubicados} con distrito nuevo, {etiquetados} atributos marcados, "
				f"{vacios} sin sublocality en Google, {fallados} con error."
			)
		)
