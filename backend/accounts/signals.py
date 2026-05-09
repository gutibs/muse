from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

from accounts.models import Friendship, Profile


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_profile(sender, instance, created, **kwargs):
	if created:
		Profile.objects.create(user=instance)
		from feed.models import Activity

		Activity.objects.create(actor=instance, verb=Activity.Verb.JOINED)


@receiver(post_save, sender=Friendship)
def create_friendship_activity(sender, instance, created, **kwargs):
	# Fire two Activity rows (one per side) when a friendship LANDS in
	# ACCEPTED. Two paths reach this state:
	#   1. created=True: the friendship is born ACCEPTED. Today the only
	#      caller is RegisterSerializer consuming an EmailInvitation
	#      (see C-008 + docs/PRODUCT_DECISIONS.md D-005).
	#   2. created=False with `status` in update_fields: the recipient
	#      accepted a PENDING request via FriendshipViewSet.partial_update
	#      (which calls .save(update_fields=["status", "updated_at"])).
	# When update_fields is unspecified (full .save()), we conservatively
	# fire — that matches the pre-C-008b behavior and avoids missing the
	# transition for any caller that doesn't pass update_fields.
	if instance.status != Friendship.Status.ACCEPTED:
		return
	update_fields = kwargs.get("update_fields")
	if not created and update_fields is not None and "status" not in update_fields:
		return

	from feed.models import Activity

	Activity.objects.create(
		actor=instance.from_user,
		verb=Activity.Verb.FRIENDSHIP,
		target_user=instance.to_user,
	)
	Activity.objects.create(
		actor=instance.to_user,
		verb=Activity.Verb.FRIENDSHIP,
		target_user=instance.from_user,
	)
