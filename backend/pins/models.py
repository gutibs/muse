from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class Persona(models.Model):
	name = models.CharField(max_length=80, unique=True)
	slug = models.SlugField(max_length=80, unique=True)
	icon = models.CharField(max_length=50, blank=True)
	color = models.CharField(max_length=7, blank=True)

	class Meta:
		db_table = "pins_persona"
		ordering = ["name"]

	def __str__(self):
		return self.name


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
	personas = models.ManyToManyField(Persona, blank=True, related_name="pins")
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		db_table = "pins_pin"
		unique_together = ("user", "restaurant")
		ordering = ["-updated_at"]

	def __str__(self):
		return f"{self.user} → {self.restaurant} ({self.status})"

	def clean(self):
		if self.status == self.Status.VISITED and self.rating is None:
			raise ValidationError("Rating is required for visited restaurants.")
		if self.status == self.Status.TO_VISIT and self.rating is not None:
			raise ValidationError("Cannot rate a restaurant you have not visited.")
