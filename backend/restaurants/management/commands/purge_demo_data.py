"""Borra los restaurantes sembrados y todo lo que cuelga de ellos.

Existe porque el borrado estaba documentado como una línea en el docstring de
`seed_demo_restaurants` y en ningún lado más. Producción llegó a tener 500
restaurantes inventados sobre 557, visibles en el catálogo como cualquier otro.

**El orden de las operaciones no es cosmético.** `analytics.Event` y
`MonthlyVenueStat` apuntan al restaurante con `SET_NULL`, y `MonthlyVenueStat`
guarda además el nombre copiado —a propósito, para que el reporte sobreviva al
borrado de un lugar—. Si se borran los restaurantes primero, esas filas quedan
con el nombre de un restaurante inventado, sin FK que permita volver a
encontrarlas, y el dashboard las sigue mostrando para siempre. Por eso analytics
se limpia **antes**.

Lo demás cascadea solo y está verificado: `Pin.restaurant` es CASCADE, y de cada
Pin cuelgan `feed.Activity` y `SharedListItem`, también CASCADE. El proyecto no
tiene ni un `post_delete`, así que un borrado masivo no dispara nada.
"""

import logging

from django.core.management.base import BaseCommand
from django.db import transaction

from restaurants.models import Restaurant

logger = logging.getLogger(__name__)


class Command(BaseCommand):
	help = "Borra los restaurantes marcados como demo, sus pins y su rastro de analytics"

	def add_arguments(self, parser):
		parser.add_argument(
			"--yes",
			action="store_true",
			help="Borra de verdad. Sin esto sólo informa, que es el default seguro.",
		)
		parser.add_argument(
			"--dry-run",
			action="store_true",
			help="Informa sin borrar. Es lo que pasa igual si no se pasa --yes.",
		)

	def handle(self, *args, **options):
		from analytics.models import Event, MonthlyVenueStat
		from feed.models import Activity
		from pins.models import Pin

		demo = Restaurant.objects.filter(is_demo=True)
		# Materializar los ids antes de tocar nada: después del primer delete el
		# queryset perezoso ya no encuentra lo mismo.
		ids = list(demo.values_list("id", flat=True))

		pins = Pin.objects.filter(restaurant_id__in=ids)
		conteos = {
			"restaurantes": len(ids),
			"pins": pins.count(),
			"actividad": Activity.objects.filter(pin__restaurant_id__in=ids).count(),
			"eventos de analytics": Event.objects.filter(restaurant_id__in=ids).count(),
			"filas mensuales": MonthlyVenueStat.objects.filter(restaurant_id__in=ids).count(),
		}

		for etiqueta, n in conteos.items():
			self.stdout.write(f"  {etiqueta}: {n}")

		if not ids:
			self.stdout.write(self.style.SUCCESS("No hay nada sembrado que borrar."))
			return

		if options["dry_run"] or not options["yes"]:
			self.stdout.write(
				self.style.WARNING("Nada se borró. Volvé a correrlo con --yes para hacerlo.")
			)
			return

		with transaction.atomic():
			# Analytics primero: es la única ventana en la que estas filas se
			# pueden identificar por FK.
			MonthlyVenueStat.objects.filter(restaurant_id__in=ids).delete()
			Event.objects.filter(restaurant_id__in=ids).delete()
			# Y recién ahora los restaurantes, que se llevan pins, actividad e
			# items de listas por cascada.
			Restaurant.objects.filter(id__in=ids).delete()

		logger.info("purge_demo_data: %s", conteos)
		self.stdout.write(self.style.SUCCESS(f"Borrados {len(ids)} restaurantes sembrados."))
