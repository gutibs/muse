from django.db import migrations, models


def copy_cuisine_to_cuisines(apps, schema_editor):
    Restaurant = apps.get_model("restaurants", "Restaurant")
    for r in Restaurant.objects.exclude(cuisine__isnull=True):
        r.cuisines.add(r.cuisine_id)


def copy_cuisines_to_cuisine(apps, schema_editor):
    Restaurant = apps.get_model("restaurants", "Restaurant")
    # Reverse: take the first cuisine in the M2M as the primary FK
    for r in Restaurant.objects.all():
        first = r.cuisines.first()
        if first:
            r.cuisine_id = first.id
            r.save(update_fields=["cuisine"])


class Migration(migrations.Migration):

    dependencies = [
        ("restaurants", "0008_alter_menuitem_image_url_alter_restaurant_image_url"),
    ]

    operations = [
        migrations.AddField(
            model_name="restaurant",
            name="cuisines",
            field=models.ManyToManyField(
                blank=True,
                related_name="restaurants",
                to="restaurants.cuisine",
            ),
        ),
        migrations.RunPython(copy_cuisine_to_cuisines, copy_cuisines_to_cuisine),
        migrations.RemoveField(
            model_name="restaurant",
            name="cuisine",
        ),
    ]
