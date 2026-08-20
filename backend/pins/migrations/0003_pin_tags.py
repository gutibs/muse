from django.db import migrations, models


class Migration(migrations.Migration):
	dependencies = [
		("pins", "0002_sharedlist"),
		# Los tags de ocasión tienen que existir antes de que 0004 copie las
		# personas encima.
		("restaurants", "0020_seed_taxonomy"),
	]

	operations = [
		migrations.AddField(
			model_name="pin",
			name="tags",
			field=models.ManyToManyField(blank=True, related_name="pins", to="restaurants.tag"),
		),
	]
