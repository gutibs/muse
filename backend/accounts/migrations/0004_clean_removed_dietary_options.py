"""One-shot cleanup of dietary values that are no longer offered in the UI.

Removes 'Pescatarian' and 'Halal' tokens, and renames 'Sin TACC' to
'Gluten-free' (the English equivalent we kept). Profiles may store
multiple comma-separated values, so each token is normalized and deduped.
"""
from django.db import migrations


_REMOVE = {"Pescatarian", "Halal"}
_RENAME = {"Sin TACC": "Gluten-free"}


def _normalize(value: str) -> str:
	seen = []
	for raw in (t.strip() for t in value.split(",")):
		if not raw or raw in _REMOVE:
			continue
		token = _RENAME.get(raw, raw)
		if token not in seen:
			seen.append(token)
	return ", ".join(seen)


def clean_dietary(apps, schema_editor):
	Profile = apps.get_model("accounts", "Profile")
	to_update = []
	for profile in Profile.objects.exclude(dietary="").only("id", "dietary"):
		cleaned = _normalize(profile.dietary)
		if cleaned != profile.dietary:
			profile.dietary = cleaned
			to_update.append(profile)
	if to_update:
		Profile.objects.bulk_update(to_update, ["dietary"])


class Migration(migrations.Migration):

	dependencies = [
		("accounts", "0003_profile_phone"),
	]

	operations = [
		migrations.RunPython(clean_dietary, migrations.RunPython.noop),
	]
