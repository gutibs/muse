from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from feed.models import Activity
from pins.models import Pin

# Fields whose change is "meaningful" enough to deserve an Activity(UPDATED)
# entry in the feed. Editing personas (M2M, separate signals), opening_hours,
# or just re-saving a Pin without diff should NOT noise the feed.
_TRACKED_FIELDS = ("rating", "comment", "status")


@receiver(pre_save, sender=Pin)
def cache_pin_before_save(sender, instance, **kwargs):
	"""Snapshot the tracked fields onto the instance so the post_save handler
	can detect a no-op edit. Storing on the instance (not a module-level
	dict) avoids races between concurrent saves of the same pk: each save
	carries its own snapshot through the signal chain in the same call
	frame, no shared state."""
	if not instance.pk:
		instance._activity_before = None
		return
	try:
		old = Pin.objects.only(*_TRACKED_FIELDS).get(pk=instance.pk)
	except Pin.DoesNotExist:
		instance._activity_before = None
		return
	instance._activity_before = tuple(getattr(old, f) for f in _TRACKED_FIELDS)


@receiver(post_save, sender=Pin)
def create_pin_activity(sender, instance, created, **kwargs):
	if created:
		verb = (
			Activity.Verb.RATED if instance.status == Pin.Status.VISITED else Activity.Verb.PINNED
		)
		Activity.objects.create(actor=instance.user, verb=verb, pin=instance)
		return

	# Update path: only emit Activity(UPDATED) if a tracked field changed.
	# Pre-fix, every .save() produced a feed entry — including saves that
	# only touched personas (M2M is a separate signal so this handler still
	# fired with no actual diff) and re-saves with no field changes at all.
	# Result was a noisy feed with "X updated their pin" repeated for
	# cosmetic edits. See AUDIT_QUALITATIVE.md sec 9.
	before = getattr(instance, "_activity_before", None)
	if before is None:
		# Snapshot wasn't taken (row vanished between signals, or the pre_save
		# receiver didn't run for some reason). Be conservative: skip the
		# activity rather than emit one that may not reflect real change.
		return
	after = tuple(getattr(instance, f) for f in _TRACKED_FIELDS)
	if before == after:
		return

	Activity.objects.create(
		actor=instance.user,
		verb=Activity.Verb.UPDATED,
		pin=instance,
	)


# TODO (out of C-006 scope): a one-shot management command
# `dedupe_pin_updates` to remove historical Activity(UPDATED) rows that
# correspond to no-op saves before this fix landed. Implement when the
# noise becomes a real product complaint.
