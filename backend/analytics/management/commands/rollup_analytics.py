"""Consolida los eventos en el agregado mensual por venue.

	python manage.py rollup_analytics            # mes en curso y el anterior
	python manage.py rollup_analytics --all      # todo el histórico

Idempotente: correrlo dos veces da lo mismo. Por default rehace el mes en
curso y el anterior, que es lo que puede haber cambiado desde ayer; el mes
anterior entra porque el primer día del mes todavía llegan eventos con
timestamp del mes que cerró.
"""

import datetime as dt

from django.core.management.base import BaseCommand
from django.utils import timezone

from analytics.models import Event
from analytics.services.reports import month_start, next_month, rollup_month


class Command(BaseCommand):
	help = "Roll analytics events up into the perpetual monthly per-venue stats."

	def add_arguments(self, parser):
		parser.add_argument(
			"--all",
			action="store_true",
			help="Rebuild every month that has events, not just the last two.",
		)

	def handle(self, *args, **options):
		current = month_start(timezone.now().date())
		previous = month_start(current - dt.timedelta(days=1))

		if options["all"]:
			oldest = Event.objects.order_by("created_at").first()
			if oldest is None:
				self.stdout.write("No events to roll up.")
				return
			month = month_start(oldest.created_at.date())
		else:
			month = previous

		written = 0
		while month <= current:
			written += rollup_month(month)
			month = next_month(month)

		self.stdout.write(self.style.SUCCESS(f"Wrote {written} monthly stat row(s)."))
