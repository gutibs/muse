"""Introduce DietaryPreference + Profile.dietary_preferences M2M.

Schema-only migration: creates the new model, adds the M2M, seeds the 5
canonical preferences. The data backfill from the legacy `dietary`
CharField + drop of that field happens in 0006 so the schema-vs-data
boundary is clean and either step can be rolled back independently.

Canonical set matches what migration 0004 left as supported (Pescatarian
and Halal were intentionally removed at that point; Sin TACC was renamed
to Gluten-free). Ver C-007 task spec.
"""
from django.db import migrations, models
from django.utils.text import slugify


SEED_PREFERENCES = [
	"Omnivore",
	"Vegetarian",
	"Vegan",
	"Kosher",
	"Gluten-free",
]


def seed_preferences(apps, schema_editor):
	DietaryPreference = apps.get_model("accounts", "DietaryPreference")
	for name in SEED_PREFERENCES:
		DietaryPreference.objects.get_or_create(
			slug=slugify(name),
			defaults={"name": name},
		)


def unseed_preferences(apps, schema_editor):
	DietaryPreference = apps.get_model("accounts", "DietaryPreference")
	DietaryPreference.objects.filter(slug__in=[slugify(n) for n in SEED_PREFERENCES]).delete()


class Migration(migrations.Migration):
	dependencies = [
		("accounts", "0004_clean_removed_dietary_options"),
	]

	operations = [
		migrations.CreateModel(
			name="DietaryPreference",
			fields=[
				("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
				("name", models.CharField(max_length=40, unique=True)),
				("slug", models.SlugField(max_length=40, unique=True)),
			],
			options={
				"db_table": "accounts_dietary_preference",
				"ordering": ["name"],
			},
		),
		migrations.AddField(
			model_name="profile",
			name="dietary_preferences",
			field=models.ManyToManyField(
				blank=True,
				related_name="profiles",
				to="accounts.dietarypreference",
			),
		),
		migrations.RunPython(seed_preferences, unseed_preferences),
	]
