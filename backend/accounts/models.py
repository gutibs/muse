import uuid

from django.conf import settings
from django.contrib.gis.db import models as gis_models
from django.db import models


class DietaryPreference(models.Model):
	"""Closed set of dietary preferences a user can have. Replaces the
	previous comma-separated CharField on Profile (see migration 0005);
	enables proper FK validation + future joins (e.g. "find friends with
	the same preferences").

	Rows are seeded by migration; not user-creatable from the app.
	"""

	name = models.CharField(max_length=40, unique=True)
	slug = models.SlugField(max_length=40, unique=True)

	class Meta:
		db_table = "accounts_dietary_preference"
		ordering = ["name"]

	def __str__(self):
		return self.name


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
	website = models.URLField(blank=True)
	instagram = models.CharField(max_length=60, blank=True)
	phone = models.CharField(max_length=20, blank=True)
	favourite_cuisine = models.ForeignKey(
		"restaurants.Cuisine",
		on_delete=models.SET_NULL,
		null=True,
		blank=True,
		related_name="+",
	)
	dietary_preferences = models.ManyToManyField(
		DietaryPreference,
		blank=True,
		related_name="profiles",
	)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		db_table = "accounts_profile"

	def __str__(self):
		return self.display_name or self.user.email or self.user.username


class ConsentRecord(models.Model):
	"""Proof that a user actively consented to a data-protection policy at a
	given point in time. One row per (user, policy) acceptance. GDPR/PDPO
	require being able to demonstrate *when* and *to which version* consent
	was given — hence policy_version + accepted_at + ip_address.

	Append-only by intent: re-consenting to a new policy version creates a new
	row, it does not overwrite the old one. Never edited from the admin.
	"""

	class Policy(models.TextChoices):
		GDPR = "gdpr", "GDPR"
		PDPO = "pdpo", "PDPO"

	user = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.CASCADE,
		related_name="consents",
	)
	policy = models.CharField(max_length=10, choices=Policy.choices)
	policy_version = models.CharField(max_length=20)
	accepted_at = models.DateTimeField(auto_now_add=True)
	ip_address = models.GenericIPAddressField(null=True, blank=True)

	class Meta:
		db_table = "accounts_consent_record"
		ordering = ["-accepted_at"]
		indexes = [models.Index(fields=["user", "policy"], name="accounts_co_user_id_idx")]

	def __str__(self):
		return f"{self.user} accepted {self.policy} v{self.policy_version}"


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
