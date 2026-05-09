"""Backfill Profile.dietary_preferences from the legacy CSV `dietary`
CharField, then drop that field.

The old field stored values like "Vegetarian, Gluten-free" (see migration
0004 for the cleanup pass). We split each row's value, look up the matching
DietaryPreference by name, and attach via the M2M. Tokens that don't match
the seeded set (typos, deprecated values) are dropped silently — migration
0004 already ran a cleanup pass against the canonical set, so any leftover
unrecognized tokens are noise we don't want to preserve.

Stats are printed during the migration so anyone running it sees how many
profiles were touched and how many tokens couldn't be matched.
"""
from django.db import migrations


def backfill(apps, schema_editor):
	Profile = apps.get_model("accounts", "Profile")
	DietaryPreference = apps.get_model("accounts", "DietaryPreference")

	by_name = {p.name: p for p in DietaryPreference.objects.all()}
	if not by_name:
		# 0005 should have seeded these; if not, fail loud rather than
		# silently lose all the legacy data.
		raise RuntimeError(
			"DietaryPreference table is empty; migration 0005 must seed before 0006 backfills."
		)

	migrated = 0
	unmatched_tokens = []
	for profile in Profile.objects.exclude(dietary="").only("id", "dietary"):
		matched = []
		for raw in (t.strip() for t in (profile.dietary or "").split(",")):
			if not raw:
				continue
			pref = by_name.get(raw)
			if pref is None:
				unmatched_tokens.append(raw)
				continue
			matched.append(pref)
		if matched:
			profile.dietary_preferences.set(matched)
			migrated += 1

	if migrated or unmatched_tokens:
		# stderr-style print so it shows in `migrate` output without
		# requiring a logger config in the migration context.
		print(
			f"  [accounts.0006] backfilled {migrated} profile(s); "
			f"dropped {len(unmatched_tokens)} unmatched token(s): "
			f"{sorted(set(unmatched_tokens))[:10]}"
		)


def reverse_backfill(apps, schema_editor):
	# Reverse: rebuild the CSV string from the M2M associations. Best-effort
	# only — the original ordering inside the CSV isn't recoverable.
	Profile = apps.get_model("accounts", "Profile")
	for profile in Profile.objects.prefetch_related("dietary_preferences").all():
		names = list(profile.dietary_preferences.values_list("name", flat=True))
		if names:
			profile.dietary = ", ".join(sorted(names))
			profile.save(update_fields=["dietary"])


class Migration(migrations.Migration):
	dependencies = [
		("accounts", "0005_dietary_preferences"),
	]

	operations = [
		migrations.RunPython(backfill, reverse_backfill),
		migrations.RemoveField(
			model_name="profile",
			name="dietary",
		),
	]
