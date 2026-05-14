"""Seed demo Pins (visited + to_visit) for a user against the demo restaurants.

Picks N restaurants tagged `demo` and creates pins for the given user:
visited pins get a random rating 1-5 (weighted toward 4-5), a short random
comment, and a random visited_at date in the last 180 days. to_visit pins
have no rating, comment, or visited_at.

Cleanup is implicit: when the demo restaurants are deleted, the pins
cascade with them. To clean up only the pins (keep restaurants):
    Pin.objects.filter(user__email='...', restaurant__tags__slug='demo').delete()

Usage:
    docker compose exec backend python manage.py seed_demo_pins \\
        --email gustavo@dothecode.com --visited 100 --to-visit 50
"""

import random
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from pins.models import Pin
from restaurants.models import Restaurant

User = get_user_model()

COMMENTS = [
	"Volvería seguro.",
	"Muy bueno, recomiendo.",
	"Excelente atención.",
	"La pasta estaba al dente.",
	"Buena relación calidad-precio.",
	"Da rifare assolutamente.",
	"Ottima cucina, ambiente accogliente.",
	"Il servizio era impeccabile.",
	"Lovely atmosphere, will come back.",
	"Great food and friendly staff.",
	"Solid choice for a casual dinner.",
	"Cocktails fueron lo más destacado.",
	"El postre, una sorpresa agradable.",
	"Un poco caro pero vale la pena.",
	"",  # Some pins have no comment.
	"",
]


def random_rating():
	"""Weighted toward 4 and 5 (most users rate generously)."""
	return random.choices([1, 2, 3, 4, 5], weights=[1, 2, 5, 12, 10])[0]


def random_visited_at():
	days_ago = random.randint(0, 180)
	return (timezone.now() - timedelta(days=days_ago)).date()


class Command(BaseCommand):
	help = "Seed visited + to_visit Pins for a user against the demo restaurants."

	def add_arguments(self, parser):
		parser.add_argument("--email", required=True, help="Pin owner email.")
		parser.add_argument("--visited", type=int, default=100, help="Visited pins (default 100).")
		parser.add_argument("--to-visit", type=int, default=50, help="to_visit pins (default 50).")
		parser.add_argument("--dry-run", action="store_true", help="Print plan without writing.")

	def handle(self, *args, **options):
		email = options["email"]
		n_visited = options["visited"]
		n_to_visit = options["to_visit"]
		dry = options["dry_run"]

		try:
			user = User.objects.get(email=email)
		except User.DoesNotExist as err:
			raise CommandError(f"User with email {email!r} not found.") from err

		# Exclude restaurants the user already has a pin for so we don't hit
		# the (user, restaurant) unique constraint.
		already_pinned = Pin.objects.filter(user=user).values_list("restaurant_id", flat=True)
		demo_restaurants = list(
			Restaurant.objects.filter(tags__slug="demo")
			.exclude(id__in=already_pinned)
			.values_list("id", flat=True)
		)

		needed = n_visited + n_to_visit
		if len(demo_restaurants) < needed:
			raise CommandError(
				f"Not enough demo restaurants without pins: need {needed}, "
				f"have {len(demo_restaurants)}. Run seed_demo_restaurants first "
				f"or pick lower numbers."
			)

		random.shuffle(demo_restaurants)
		visited_ids = demo_restaurants[:n_visited]
		to_visit_ids = demo_restaurants[n_visited : n_visited + n_to_visit]

		self.stdout.write(
			self.style.NOTICE(
				f"Plan: {n_visited} visited + {n_to_visit} to_visit pins for {email} (id={user.id})"
			)
		)
		self.stdout.write(f"  Demo restaurants available: {len(demo_restaurants)}")

		if dry:
			self.stdout.write(self.style.WARNING("--dry-run: no writes performed."))
			return

		created_visited = 0
		created_to_visit = 0
		with transaction.atomic():
			for rid in visited_ids:
				Pin.objects.create(
					user=user,
					restaurant_id=rid,
					status=Pin.Status.VISITED,
					rating=random_rating(),
					comment=random.choice(COMMENTS),
					visited_at=random_visited_at(),
				)
				created_visited += 1

			for rid in to_visit_ids:
				Pin.objects.create(
					user=user,
					restaurant_id=rid,
					status=Pin.Status.TO_VISIT,
				)
				created_to_visit += 1

		self.stdout.write(
			self.style.SUCCESS(
				f"Done. Created {created_visited} visited + {created_to_visit} to_visit pins."
			)
		)
