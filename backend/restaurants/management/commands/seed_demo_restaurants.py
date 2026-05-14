"""Seed demo restaurants for a user across Buenos Aires, Rome, and London.

Every restaurant created gets the `demo` Tag, so cleanup is a single query:
    Restaurant.objects.filter(tags__slug="demo").delete()

Run on prod (via SSH to EC2):
    docker compose exec backend python manage.py seed_demo_restaurants \\
        --email gustavo@dothecode.com --count 500
"""

import random

from django.contrib.auth import get_user_model
from django.contrib.gis.geos import Point
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.text import slugify

from restaurants.models import Cuisine, Restaurant, Tag

User = get_user_model()

CITIES = [
	{
		"name": "Buenos Aires",
		"country": "Argentina",
		"lat": -34.6037,
		"lng": -58.3816,
		"jitter": 0.05,
		"streets": [
			"Av. Corrientes",
			"Av. Santa Fe",
			"Av. Cabildo",
			"Av. Rivadavia",
			"Defensa",
			"Florida",
			"Honduras",
			"Gorriti",
			"Thames",
			"Costa Rica",
			"Borges",
			"Armenia",
			"Malabia",
			"El Salvador",
		],
		"name_prefixes": [
			"El",
			"La",
			"Don",
			"Doña",
			"Almacén",
			"Bodegón",
			"Café",
			"Pizzería",
			"Parrilla",
			"Boliche",
		],
		"name_middles": [
			"Quincho",
			"Fuelle",
			"Tano",
			"Gallego",
			"Patio",
			"Rincón",
			"Asador",
			"Esquina",
			"Tasca",
			"Mercado",
			"Galpón",
			"Refugio",
		],
		"name_suffixes": [
			"de Palermo",
			"de San Telmo",
			"de Recoleta",
			"del Centro",
			"de Belgrano",
			"de Caballito",
			"del Abasto",
			"de Núñez",
		],
	},
	{
		"name": "Rome",
		"country": "Italy",
		"lat": 41.9028,
		"lng": 12.4964,
		"jitter": 0.05,
		"streets": [
			"Via del Corso",
			"Via Veneto",
			"Via Condotti",
			"Via Margutta",
			"Via dei Coronari",
			"Via Giulia",
			"Via del Boschetto",
			"Via Urbana",
			"Via Panisperna",
			"Vicolo del Cinque",
			"Via Trastevere",
			"Piazza Navona",
			"Piazza di Spagna",
		],
		"name_prefixes": [
			"Trattoria",
			"Osteria",
			"Ristorante",
			"Pizzeria",
			"Antica",
			"Da",
			"Il",
			"La",
		],
		"name_middles": [
			"Mario",
			"Gianni",
			"Luigi",
			"Carlo",
			"Forno",
			"Cantina",
			"Vino",
			"Pasta",
			"Grotta",
			"Lupo",
			"Toscana",
			"Rustica",
			"Romana",
			"Nonna",
		],
		"name_suffixes": [
			"di Trastevere",
			"del Pantheon",
			"di Monti",
			"del Centro",
			"di Testaccio",
			"del Ghetto",
			"ai Quattro Venti",
		],
	},
	{
		"name": "London",
		"country": "United Kingdom",
		"lat": 51.5074,
		"lng": -0.1278,
		"jitter": 0.05,
		"streets": [
			"Oxford St",
			"Carnaby St",
			"Brick Lane",
			"Old Compton St",
			"Berwick St",
			"Shoreditch High St",
			"Hackney Rd",
			"Camden High St",
			"Portobello Rd",
			"Notting Hill Gate",
			"Borough High St",
			"Brixton Rd",
			"King's Rd",
		],
		"name_prefixes": [
			"The",
			"Ye Olde",
		],
		"name_middles": [
			"Crown",
			"King's Head",
			"Lion",
			"Fox",
			"Anchor",
			"Rose",
			"Bell",
			"Garden",
			"Black Horse",
			"Red Lion",
			"White Hart",
			"Bull",
			"Tavern",
			"Chop House",
			"Tea Room",
			"Bistro",
			"Curry House",
			"Counter",
			"Kitchen",
			"Larder",
		],
		"name_suffixes": [
			"of Soho",
			"of Camden",
			"of Shoreditch",
			"of Notting Hill",
			"of Marylebone",
			"of Hoxton",
			"of Brixton",
			"of Mayfair",
		],
	},
]

DEFAULT_CUISINES = [
	"Italian",
	"Pizza",
	"Burger",
	"Sushi",
	"Argentine",
	"British",
	"Indian",
	"Mediterranean",
	"Asian",
	"Mexican",
]


def ensure_cuisines():
	created = 0
	for name in DEFAULT_CUISINES:
		_, was_created = Cuisine.objects.get_or_create(slug=slugify(name), defaults={"name": name})
		if was_created:
			created += 1
	return created


def ensure_demo_tag():
	tag, _ = Tag.objects.get_or_create(
		slug="demo",
		defaults={"name": "Demo", "kind": Tag.Kind.GENERAL},
	)
	return tag


def make_name(city, taken):
	"""Combine prefix + middle (+ optional suffix) until we get something unique."""
	for _ in range(20):
		parts = [random.choice(city["name_prefixes"]), random.choice(city["name_middles"])]
		if random.random() < 0.45:
			parts.append(random.choice(city["name_suffixes"]))
		name = " ".join(parts)
		if name not in taken:
			taken.add(name)
			return name
	# Fallback: append a number to disambiguate.
	base = " ".join([random.choice(city["name_prefixes"]), random.choice(city["name_middles"])])
	i = 2
	while f"{base} {i}" in taken:
		i += 1
	name = f"{base} {i}"
	taken.add(name)
	return name


class Command(BaseCommand):
	help = (
		"Seed N demo restaurants for a user across BA / Rome / London. "
		"All restaurants get the `demo` Tag for easy cleanup."
	)

	def add_arguments(self, parser):
		parser.add_argument("--email", required=True, help="Owner email.")
		parser.add_argument(
			"--count", type=int, default=500, help="Total restaurants (default 500)."
		)
		parser.add_argument(
			"--status",
			choices=[Restaurant.ApprovalStatus.APPROVED, Restaurant.ApprovalStatus.PENDING],
			default=Restaurant.ApprovalStatus.APPROVED,
			help="approval_status of created restaurants (default approved).",
		)
		parser.add_argument(
			"--dry-run",
			action="store_true",
			help="Print plan and exit without writing.",
		)

	def handle(self, *args, **options):
		email = options["email"]
		count = options["count"]
		status = options["status"]
		dry = options["dry_run"]

		try:
			user = User.objects.get(email=email)
		except User.DoesNotExist as err:
			raise CommandError(f"User with email {email!r} not found.") from err

		# Distribute count across cities as evenly as possible.
		per_city = [count // 3] * 3
		for i in range(count % 3):
			per_city[i] += 1

		self.stdout.write(
			self.style.NOTICE(
				f"Plan: {count} restaurants for {email} (id={user.id}), status={status}"
			)
		)
		for city, n in zip(CITIES, per_city, strict=False):
			self.stdout.write(f"  {city['name']}: {n}")

		if dry:
			self.stdout.write(self.style.WARNING("--dry-run: no writes performed."))
			return

		created_cuisines = ensure_cuisines()
		if created_cuisines:
			self.stdout.write(f"Seeded {created_cuisines} cuisines.")

		demo_tag = ensure_demo_tag()
		cuisines = list(Cuisine.objects.all())
		taken_names = set(Restaurant.objects.values_list("name", flat=True))

		total = 0
		with transaction.atomic():
			for city, n in zip(CITIES, per_city, strict=False):
				for _ in range(n):
					name = make_name(city, taken_names)
					lat = city["lat"] + random.uniform(-city["jitter"], city["jitter"])
					lng = city["lng"] + random.uniform(-city["jitter"], city["jitter"])
					street = random.choice(city["streets"])
					number = random.randint(1, 9999)
					r = Restaurant.objects.create(
						name=name,
						location=Point(lng, lat, srid=4326),
						approval_status=status,
						address=f"{street} {number}",
						city=city["name"],
						country=city["country"],
						price_level=random.randint(1, 4),
						quality_level=random.randint(2, 5),
						created_by=user,
					)
					# 1–3 cuisines, weighted toward 1–2.
					n_cuisines = random.choices([1, 2, 3], weights=[5, 4, 1])[0]
					r.cuisines.set(random.sample(cuisines, k=min(n_cuisines, len(cuisines))))
					r.tags.add(demo_tag)
					total += 1
				self.stdout.write(self.style.SUCCESS(f"  {city['name']}: +{n}"))

		self.stdout.write(
			self.style.SUCCESS(
				f"Done. Created {total} restaurants. "
				f"Cleanup later with: Restaurant.objects.filter(tags__slug='demo').delete()"
			)
		)
