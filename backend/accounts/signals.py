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
	if not created and instance.status == Friendship.Status.ACCEPTED:
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
