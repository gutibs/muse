"""ConsentRecord: append-only proof of GDPR/PDPO consent given at registration.

Schema-only. Existing users have no rows (they predate active consent); a
future re-consent flow would backfill or prompt them. New registrations
always create two rows (one per policy) — see RegisterSerializer.
"""

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
	dependencies = [
		migrations.swappable_dependency(settings.AUTH_USER_MODEL),
		("accounts", "0006_backfill_dietary_then_drop"),
	]

	operations = [
		migrations.CreateModel(
			name="ConsentRecord",
			fields=[
				(
					"id",
					models.BigAutoField(
						auto_created=True,
						primary_key=True,
						serialize=False,
						verbose_name="ID",
					),
				),
				(
					"policy",
					models.CharField(
						choices=[("gdpr", "GDPR"), ("pdpo", "PDPO")], max_length=10
					),
				),
				("policy_version", models.CharField(max_length=20)),
				("accepted_at", models.DateTimeField(auto_now_add=True)),
				("ip_address", models.GenericIPAddressField(blank=True, null=True)),
				(
					"user",
					models.ForeignKey(
						on_delete=django.db.models.deletion.CASCADE,
						related_name="consents",
						to=settings.AUTH_USER_MODEL,
					),
				),
			],
			options={
				"db_table": "accounts_consent_record",
				"ordering": ["-accepted_at"],
			},
		),
		migrations.AddIndex(
			model_name="consentrecord",
			index=models.Index(
				fields=["user", "policy"], name="accounts_co_user_id_idx"
			),
		),
	]
