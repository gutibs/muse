from django.conf import settings
from django.db import models


class Activity(models.Model):
	class Verb(models.TextChoices):
		PINNED = "pinned", "pinned"
		RATED = "rated", "rated"
		UPDATED = "updated", "updated"
		JOINED = "joined", "joined"
		FRIENDSHIP = "friendship", "became friends with"

	actor = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.CASCADE,
		related_name="activities",
	)
	verb = models.CharField(max_length=20, choices=Verb.choices)
	pin = models.ForeignKey(
		"pins.Pin",
		on_delete=models.CASCADE,
		null=True,
		blank=True,
		related_name="activities",
	)
	target_user = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.CASCADE,
		null=True,
		blank=True,
		related_name="activities_targeted",
	)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		db_table = "feed_activity"
		ordering = ["-created_at"]
		indexes = [
			models.Index(fields=["-created_at"]),
			models.Index(fields=["actor", "-created_at"]),
		]
		verbose_name_plural = "activities"

	def __str__(self):
		target = self.pin or self.target_user or ""
		return f"{self.actor} {self.verb} {target}"
