import uuid

from django.conf import settings
from django.contrib.gis.db import models as gis_models
from django.db import models


class Profile(models.Model):
	user = models.OneToOneField(
		settings.AUTH_USER_MODEL,
		on_delete=models.CASCADE,
		related_name="profile",
	)
	display_name = models.CharField(max_length=100, blank=True)
	bio = models.CharField(max_length=300, blank=True)
	avatar = models.ImageField(upload_to="avatars/", blank=True)
	city = models.CharField(max_length=100, blank=True)
	location = gis_models.PointField(null=True, blank=True, srid=4326)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		db_table = "accounts_profile"

	def __str__(self):
		return self.display_name or self.user.email or self.user.username


class Friendship(models.Model):
	class Status(models.TextChoices):
		PENDING = "pending", "Pending"
		ACCEPTED = "accepted", "Accepted"
		DECLINED = "declined", "Declined"

	from_user = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.CASCADE,
		related_name="friendships_sent",
	)
	to_user = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.CASCADE,
		related_name="friendships_received",
	)
	status = models.CharField(
		max_length=10,
		choices=Status.choices,
		default=Status.PENDING,
	)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		db_table = "accounts_friendship"
		unique_together = ("from_user", "to_user")
		ordering = ["-created_at"]

	def __str__(self):
		return f"{self.from_user} → {self.to_user} ({self.status})"


class EmailInvitation(models.Model):
	from_user = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.CASCADE,
		related_name="invitations_sent",
	)
	email = models.EmailField()
	token = models.UUIDField(default=uuid.uuid4, unique=True)
	accepted = models.BooleanField(default=False)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		db_table = "accounts_email_invitation"
		unique_together = ("from_user", "email")

	def __str__(self):
		return f"{self.from_user} invited {self.email}"
