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
	image_url = models.URLField(blank=True)
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


class MenuItem(models.Model):
	class Category(models.TextChoices):
		STARTER = "starter", "Starter"
		MAIN = "main", "Main"
		DESSERT = "dessert", "Dessert"
		DRINK = "drink", "Drink"
		SIDE = "side", "Side"

	restaurant = models.ForeignKey(
		Restaurant,
		on_delete=models.CASCADE,
		related_name="menu_items",
	)
	name = models.CharField(max_length=200)
	description = models.CharField(max_length=500, blank=True)
	price = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
	currency = models.CharField(max_length=3, default="USD")
	category = models.CharField(max_length=10, choices=Category.choices, default=Category.MAIN)
	is_recommended = models.BooleanField(default=False)
	is_vegetarian = models.BooleanField(default=False)
	is_gluten_free = models.BooleanField(default=False)
	image_url = models.URLField(blank=True)

	class Meta:
		db_table = "restaurants_menu_item"
		ordering = ["category", "name"]

	def __str__(self):
		return f"{self.name} — {self.restaurant.name}"
