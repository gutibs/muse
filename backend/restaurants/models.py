from django.conf import settings
from django.contrib.gis.db import models as gis_models
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class Cuisine(models.Model):
	name = models.CharField(max_length=80, unique=True)
	slug = models.SlugField(max_length=80, unique=True)

	class Meta:
		db_table = "restaurants_cuisine"
		ordering = ["name"]

	def __str__(self):
		return self.name


class Tag(models.Model):
	name = models.CharField(max_length=80, unique=True)
	slug = models.SlugField(max_length=80, unique=True)

	class Meta:
		db_table = "restaurants_tag"
		ordering = ["name"]

	def __str__(self):
		return self.name


class Restaurant(models.Model):
	name = models.CharField(max_length=200)
	location = gis_models.PointField(srid=4326)
	address = models.CharField(max_length=300, blank=True)
	city = models.CharField(max_length=100, blank=True, db_index=True)
	country = models.CharField(max_length=100, blank=True)
	cuisine = models.ForeignKey(
		Cuisine,
		on_delete=models.SET_NULL,
		null=True,
		blank=True,
		related_name="restaurants",
	)
	tags = models.ManyToManyField(Tag, blank=True, related_name="restaurants")
	price_level = models.PositiveSmallIntegerField(
		null=True,
		blank=True,
		validators=[MinValueValidator(1), MaxValueValidator(5)],
	)
	quality_level = models.PositiveSmallIntegerField(
		null=True,
		blank=True,
		validators=[MinValueValidator(1), MaxValueValidator(5)],
	)
	website = models.URLField(blank=True)
	phone = models.CharField(max_length=30, blank=True)
	created_by = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.SET_NULL,
		null=True,
		related_name="restaurants_created",
	)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		db_table = "restaurants_restaurant"

	def __str__(self):
		return f"{self.name} ({self.city})" if self.city else self.name
