"""Pin signals: Activity(UPDATED) only fires for meaningful changes.

Pre-fix, any .save() emitted UPDATED — including saves that only touched
personas (M2M, which doesn't even change Pin fields) and re-saves with no
diff. Result: feed got noisy with "X updated their pin" repeated for
cosmetic edits. Fix in C-006: pre_save snapshots tracked fields, post_save
compares.
"""

import pytest

from feed.models import Activity
from pins.models import Persona, Pin
from tests.factories import PinFactory, RestaurantFactory, UserFactory


def _activities_for(pin):
	return Activity.objects.filter(pin=pin)


@pytest.mark.critical
@pytest.mark.django_db
def test_pin_create_emits_pinned_or_rated():
	"""Sanity: create still emits an Activity, with the right verb."""
	user = UserFactory()
	to_visit = PinFactory(user=user, restaurant=RestaurantFactory())
	visited = PinFactory(
		user=user,
		restaurant=RestaurantFactory(),
		status=Pin.Status.VISITED,
		rating=4,
	)

	to_visit_acts = _activities_for(to_visit)
	visited_acts = _activities_for(visited)
	assert to_visit_acts.count() == 1
	assert to_visit_acts.first().verb == Activity.Verb.PINNED
	assert visited_acts.count() == 1
	assert visited_acts.first().verb == Activity.Verb.RATED


@pytest.mark.critical
@pytest.mark.django_db
def test_pin_update_personas_does_not_emit_activity():
	"""M2M edits + save() with no tracked-field change → no UPDATED row."""
	user = UserFactory()
	pin = PinFactory(user=user, restaurant=RestaurantFactory())
	persona = Persona.objects.create(name="Date night", slug="date-night")

	count_before = Activity.objects.count()
	pin.personas.add(persona)
	pin.save()

	assert (
		Activity.objects.count() == count_before
	), "Adding a persona + re-saving must not produce an UPDATED feed row"


@pytest.mark.critical
@pytest.mark.django_db
def test_pin_update_rating_emits_updated():
	user = UserFactory()
	pin = PinFactory(
		user=user,
		restaurant=RestaurantFactory(),
		status=Pin.Status.VISITED,
		rating=3,
	)
	count_before = Activity.objects.count()

	pin.rating = 5
	pin.save()

	assert Activity.objects.count() == count_before + 1
	last = Activity.objects.filter(pin=pin).order_by("-created_at").first()
	assert last.verb == Activity.Verb.UPDATED


@pytest.mark.critical
@pytest.mark.django_db
def test_pin_update_comment_emits_updated():
	user = UserFactory()
	pin = PinFactory(
		user=user,
		restaurant=RestaurantFactory(),
		status=Pin.Status.VISITED,
		rating=4,
		comment="old",
	)
	count_before = Activity.objects.count()

	pin.comment = "new"
	pin.save()

	assert Activity.objects.count() == count_before + 1


@pytest.mark.critical
@pytest.mark.django_db
def test_pin_save_with_no_change_does_not_emit_activity():
	"""Idempotent re-save (no field change) → no new UPDATED row."""
	user = UserFactory()
	pin = PinFactory(
		user=user,
		restaurant=RestaurantFactory(),
		status=Pin.Status.VISITED,
		rating=4,
		comment="great",
	)
	count_before = Activity.objects.count()

	pin.save()  # nothing changed
	pin.save()

	assert Activity.objects.count() == count_before
