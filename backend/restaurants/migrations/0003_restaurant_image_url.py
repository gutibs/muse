from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("restaurants", "0002_tag_restaurant_quality_level_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="restaurant",
            name="image_url",
            field=models.URLField(blank=True),
        ),
    ]
