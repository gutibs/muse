"""Pending no-op left over from DEFAULT_AUTO_FIELD, split out of 0008.

DietaryPreference was created with an AutoField before the project settled on
BigAutoField; makemigrations has been dragging this AlterField along ever
since. Kept separate so the erasure migration stays readable — this one is
unrelated to it. Cheap: the table holds a handful of seeded rows.
"""

from django.db import migrations, models


class Migration(migrations.Migration):
	dependencies = [
		("accounts", "0008_profile_deleted_at"),
	]

	operations = [
		migrations.AlterField(
			model_name="dietarypreference",
			name="id",
			field=models.BigAutoField(
				auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
			),
		),
	]
