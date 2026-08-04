"""Profile.deleted_at: marks an account erased under GDPR art. 17 / PDPO.

Schema-only. The row survives erasure on purpose so the person's reviews keep
a valid FK while losing their byline — see accounts.services.account_deletion
and docs/PRODUCT_DECISIONS.md D-009.
"""

from django.db import migrations, models


class Migration(migrations.Migration):
	dependencies = [
		("accounts", "0007_consent_record"),
	]

	operations = [
		migrations.AddField(
			model_name="profile",
			name="deleted_at",
			field=models.DateTimeField(blank=True, null=True),
		),
	]
