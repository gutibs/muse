import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("pins", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="SharedList",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("token", models.UUIDField(default=uuid.uuid4, unique=True, db_index=True)),
                ("title", models.CharField(blank=True, max_length=200)),
                ("status_filter", models.CharField(choices=[("all", "All"), ("visited", "Visited"), ("to_visit", "To Visit")], default="all", max_length=10)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="shared_lists", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "db_table": "pins_shared_list",
                "ordering": ["-created_at"],
            },
        ),
    ]
