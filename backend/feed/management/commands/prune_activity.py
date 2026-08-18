"""Delete Activity rows older than N days so the feed table does not grow unbounded.

Run from a cron/scheduler in production, e.g.:
    docker compose exec backend python manage.py prune_activity --days 90
"""

from datetime import timedelta

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from feed.models import Activity

MIN_RETENTION_DAYS = 1


class Command(BaseCommand):
	help = "Prune Activity rows older than N days (default 90)."

	def add_arguments(self, parser):
		parser.add_argument(
			"--days",
			type=int,
			default=90,
			help="Delete activity older than this many days.",
		)

	def handle(self, *args, **options):
		days = options["days"]
		# Sin este chequeo, `--days 0` (típico de una env var vacía en el cron que
		# templatea el comando) pone el cutoff en `now` y borra el feed entero de
		# todos los usuarios, con exit 0 y un SUCCESS verde. Negativo es peor: el
		# cutoff se va al futuro.
		if days < MIN_RETENTION_DAYS:
			raise CommandError(
				f"--days debe ser >= {MIN_RETENTION_DAYS} (recibido: {days}). "
				"Un valor menor borraría toda la tabla Activity."
			)

		cutoff = timezone.now() - timedelta(days=days)
		deleted, _ = Activity.objects.filter(created_at__lt=cutoff).delete()
		self.stdout.write(
			self.style.SUCCESS(f"Deleted {deleted} activities older than {options['days']} days.")
		)
