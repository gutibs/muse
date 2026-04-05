from django.db.models.signals import post_save
from django.dispatch import receiver

from feed.models import Activity
from pins.models import Pin


@receiver(post_save, sender=Pin)
def create_pin_activity(sender, instance, created, **kwargs):
	if created:
		verb = (
			Activity.Verb.RATED
			if instance.status == Pin.Status.VISITED
			else Activity.Verb.PINNED
		)
	else:
		verb = Activity.Verb.UPDATED

	Activity.objects.create(
		actor=instance.user,
		verb=verb,
		pin=instance,
	)
