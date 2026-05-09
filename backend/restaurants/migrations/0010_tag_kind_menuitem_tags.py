"""C-005 commit 1: schema-only.

Adds Tag.kind (with db_index) for distinguishing dietary / general /
highlight tags, and MenuItem.tags M2M. Booleans (is_vegetarian,
is_gluten_free, is_recommended) stay in this migration; commit 2 copies
them to the M2M, commit 3 drops them.
"""
from django.db import migrations, models


class Migration(migrations.Migration):
	dependencies = [
		("restaurants", "0009_restaurant_cuisines_m2m"),
	]

	operations = [
		migrations.AddField(
			model_name="tag",
			name="kind",
			field=models.CharField(
				choices=[
					("dietary", "Dietary"),
					("general", "General"),
					("highlight", "Highlight"),
				],
				db_index=True,
				default="general",
				max_length=20,
			),
		),
		migrations.AddField(
			model_name="menuitem",
			name="tags",
			field=models.ManyToManyField(
				blank=True,
				related_name="menu_items",
				to="restaurants.tag",
			),
		),
	]
