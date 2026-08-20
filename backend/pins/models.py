import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class Pin(models.Model):
	class Status(models.TextChoices):
		VISITED = "visited", "Visited"
		TO_VISIT = "to_visit", "To Visit"

	user = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.CASCADE,
		related_name="pins",
	)
	restaurant = models.ForeignKey(
		"restaurants.Restaurant",
		on_delete=models.CASCADE,
		related_name="pins",
	)
	status = models.CharField(
		max_length=10,
		choices=Status.choices,
		default=Status.TO_VISIT,
	)
	rating = models.PositiveSmallIntegerField(
		null=True,
		blank=True,
		validators=[MinValueValidator(1), MaxValueValidator(5)],
	)
	comment = models.TextField(blank=True, max_length=2000)
	visited_at = models.DateField(null=True, blank=True)
	# Los tres ejes (vibe, occasion, scene) cuelgan del Pin y no del
	# Restaurant: son la opinión de quien lo guardó. Con el vibe en el
	# restaurante, dos personas con opiniones distintas se pisan, y sólo el
	# creador podría editarlo.
	tags = models.ManyToManyField("restaurants.Tag", blank=True, related_name="pins")
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		db_table = "pins_pin"
		unique_together = ("user", "restaurant")
		ordering = ["-updated_at"]

	def __str__(self):
		return f"{self.user} → {self.restaurant} ({self.status})"

	def clean(self):
		# Canonical source of truth for status<->rating invariant. Also
		# duplicated in PinSerializer.validate so DRF returns a clean 400
		# at the API boundary; this guard catches direct ORM writes that
		# would otherwise persist invalid combos.
		super().clean()
		if self.status == self.Status.VISITED and self.rating is None:
			raise ValidationError({"rating": "Rating is required for visited restaurants."})
		if self.status == self.Status.TO_VISIT and self.rating is not None:
			raise ValidationError({"rating": "Cannot rate a restaurant you have not visited."})

	def save(self, *args, **kwargs):
		# clean_fields + clean, guaranteeing the status<->rating invariant
		# lands even when callers go through .objects.create / .save directly.
		#
		# validate_unique=False on purpose: uniqueness is left to the database
		# constraint. Checking it here raised Django's ValidationError before
		# the INSERT, which DRF does not translate, so pinning an
		# already-pinned restaurant 500'd instead of reaching the IntegrityError
		# handler in PinViewSet.create that answers 409 with the existing pin
		# id. Letting the constraint fire also drops one SELECT per save and
		# closes the check-then-insert race between two concurrent requests.
		self.full_clean(validate_unique=False)
		super().save(*args, **kwargs)


class SharedList(models.Model):
	user = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.CASCADE,
		related_name="shared_lists",
	)
	token = models.UUIDField(default=uuid.uuid4, unique=True, db_index=True)
	title = models.CharField(max_length=200, blank=True)
	status_filter = models.CharField(
		max_length=10,
		choices=[("all", "All"), *Pin.Status.choices],
		default="all",
	)
	is_active = models.BooleanField(default=True)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		db_table = "pins_shared_list"
		ordering = ["-created_at"]

	def __str__(self):
		return f"{self.user} — {self.title or 'My List'} ({self.token})"
