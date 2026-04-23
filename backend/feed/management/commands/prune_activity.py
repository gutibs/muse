"""Delete Activity rows older than N days so the feed table does not grow unbounded.

Run from a cron/scheduler in production, e.g.:
    docker compose exec backend python manage.py prune_activity --days 90
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta

from feed.models import Activity


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
		cutoff = timezone.now() - timedelta(days=options["days"])
		deleted, _ = Activity.objects.filter(created_at__lt=cutoff).delete()
		self.stdout.write(
			self.style.SUCCESS(f"Deleted {deleted} activities older than {options['days']} days.")
		)
