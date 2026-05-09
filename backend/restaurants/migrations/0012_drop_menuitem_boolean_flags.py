"""C-005 commit 3: schema cleanup.

Drops the legacy boolean flags from MenuItem now that the M2M backfill
in 0011 has landed. Reversing this migration restores the columns
(empty); reversing 0011 then re-derives them from the M2M.
"""
from django.db import migrations


class Migration(migrations.Migration):
	dependencies = [
		("restaurants", "0011_backfill_menuitem_tags"),
	]

	operations = [
		migrations.RemoveField(model_name="menuitem", name="is_recommended"),
		migrations.RemoveField(model_name="menuitem", name="is_vegetarian"),
		migrations.RemoveField(model_name="menuitem", name="is_gluten_free"),
	]
