"""C-005 commit 2: data-only.

Seeds the 3 canonical Tag rows the boolean flags map to, then for every
MenuItem with a True flag, attaches the corresponding Tag via the M2M.

Reverse: rebuild the boolean flags from the tag M2M presence so a
rollback is non-destructive (the column still exists at this point;
commit 3 drops it).
"""
from django.db import migrations


SEED_TAGS = [
	("vegetarian", "Vegetarian", "dietary"),
	("gluten-free", "Gluten-Free", "dietary"),
	("recommended", "Recommended", "highlight"),
]


def backfill(apps, schema_editor):
	Tag = apps.get_model("restaurants", "Tag")
	MenuItem = apps.get_model("restaurants", "MenuItem")

	tags_by_slug = {}
	for slug, name, kind in SEED_TAGS:
		tag, _ = Tag.objects.get_or_create(
			slug=slug,
			defaults={"name": name, "kind": kind},
		)
		# Force the kind in case the row was pre-existing with a default
		# 'general' kind from migration 0010 backfill of an older Tag.
		if tag.kind != kind:
			tag.kind = kind
			tag.save(update_fields=["kind"])
		tags_by_slug[slug] = tag

	migrated = {"vegetarian": 0, "gluten-free": 0, "recommended": 0}
	for item in MenuItem.objects.all().only("id", "is_vegetarian", "is_gluten_free", "is_recommended"):
		additions = []
		if item.is_vegetarian:
			additions.append(tags_by_slug["vegetarian"])
			migrated["vegetarian"] += 1
		if item.is_gluten_free:
			additions.append(tags_by_slug["gluten-free"])
			migrated["gluten-free"] += 1
		if item.is_recommended:
			additions.append(tags_by_slug["recommended"])
			migrated["recommended"] += 1
		if additions:
			item.tags.add(*additions)

	if any(migrated.values()):
		print(
			f"  [restaurants.0011] migrated tags: "
			f"vegetarian={migrated['vegetarian']}, "
			f"gluten-free={migrated['gluten-free']}, "
			f"recommended={migrated['recommended']}"
		)


def reverse_backfill(apps, schema_editor):
	MenuItem = apps.get_model("restaurants", "MenuItem")
	for item in MenuItem.objects.all().prefetch_related("tags"):
		slugs = set(item.tags.values_list("slug", flat=True))
		item.is_vegetarian = "vegetarian" in slugs
		item.is_gluten_free = "gluten-free" in slugs
		item.is_recommended = "recommended" in slugs
		item.save(update_fields=["is_vegetarian", "is_gluten_free", "is_recommended"])


class Migration(migrations.Migration):
	dependencies = [
		("restaurants", "0010_tag_kind_menuitem_tags"),
	]

	operations = [
		migrations.RunPython(backfill, reverse_backfill),
	]
