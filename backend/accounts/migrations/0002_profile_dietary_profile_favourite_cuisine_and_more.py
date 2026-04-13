import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0001_initial"),
        ("restaurants", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="profile",
            name="dietary",
            field=models.CharField(blank=True, max_length=50),
        ),
        migrations.AddField(
            model_name="profile",
            name="favourite_cuisine",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="+",
                to="restaurants.cuisine",
            ),
        ),
        migrations.AddField(
            model_name="profile",
            name="instagram",
            field=models.CharField(blank=True, max_length=60),
        ),
        migrations.AddField(
            model_name="profile",
            name="website",
            field=models.URLField(blank=True),
        ),
    ]
