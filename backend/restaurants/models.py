from django.conf import settings
from django.contrib.gis.db import models as gis_models
from django.core.validators import MaxValueValidator, MinValueValidator, URLValidator
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
	class Kind(models.TextChoices):
		DIETARY = "dietary", "Dietary"
		GENERAL = "general", "General"
		HIGHLIGHT = "highlight", "Highlight"
		# Los tres ejes con los que la gente describe un lugar. Viven en un
		# solo modelo, distinguidos por kind, y no en tres: así un filtro
		# puede cruzarlos y una etiqueta nueva no necesita una tabla nueva.
		# `occasion` reemplaza al modelo Persona, que era esto mismo en otra
		# app y sin forma de combinarse con el resto.
		VIBE = "vibe", "Vibe"
		OCCASION = "occasion", "Occasion"
		SCENE = "scene", "Scene"

	name = models.CharField(max_length=80, unique=True)
	slug = models.SlugField(max_length=80, unique=True)
	kind = models.CharField(
		max_length=20,
		choices=Kind.choices,
		default=Kind.GENERAL,
		db_index=True,
	)

	class Meta:
		db_table = "restaurants_tag"
		ordering = ["name"]

	def __str__(self):
		return self.name


class Restaurant(models.Model):
	class ApprovalStatus(models.TextChoices):
		PENDING = "pending", "Pending Review"
		APPROVED = "approved", "Approved"
		REJECTED = "rejected", "Rejected"

	class ReservationProvider(models.TextChoices):
		OPENTABLE = "opentable", "OpenTable"
		THEFORK = "thefork", "TheFork"
		RESY = "resy", "Resy"
		SEVENROOMS = "sevenrooms", "SevenRooms"
		QUANDOO = "quandoo", "Quandoo"
		TABLECHECK = "tablecheck", "TableCheck"
		MEITRE = "meitre", "Meitre"
		WOKI = "woki", "Woki"
		TOCK = "tock", "Tock"
		COVERMANAGER = "covermanager", "CoverManager"
		DIRECT = "direct", "Restaurant's own site"
		OTHER = "other", "Other"

	class ReservationStatus(models.TextChoices):
		PENDING = "pending", "Pending Review"
		APPROVED = "approved", "Approved"
		REJECTED = "rejected", "Rejected"

	name = models.CharField(max_length=200)
	location = gis_models.PointField(srid=4326)
	approval_status = models.CharField(
		max_length=10,
		choices=ApprovalStatus.choices,
		default=ApprovalStatus.PENDING,
		db_index=True,
	)
	# El lugar cerró para siempre. No se borra la fila: `Pin.restaurant` es
	# CASCADE y se llevaría las reseñas de la gente. Tampoco alcanza
	# `approval_status`, que significa otra cosa y además esconde la ficha de
	# quien no la creó — justo la que necesita ver el que tiene el pin.
	# Se oculta donde alguien podría descubrirlo (listas, cerca mío) y se
	# conserva donde alguien ya lo tiene (su ficha, su pin).
	is_closed = models.BooleanField(default=False, db_index=True)
	address = models.CharField(max_length=300, blank=True)
	city = models.CharField(max_length=100, blank=True, db_index=True)
	# El barrio, de `sublocality` en el payload de Google. Es como la gente
	# ubica un lugar —Sheung Wan, Palermo— mucho más que la ciudad, que para
	# todo el catálogo porteño dice lo mismo. Indexado porque el filtro por
	# barrio es lo que viene.
	district = models.CharField(max_length=120, blank=True, db_index=True)
	country = models.CharField(max_length=100, blank=True)
	cuisines = models.ManyToManyField(Cuisine, blank=True, related_name="restaurants")
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
	image_url = models.URLField(max_length=2000, blank=True)
	website = models.URLField(max_length=500, blank=True)
	# La carga la puede hacer quien da de alta el restaurante, y el botón lo
	# ve todo el mundo: hasta que `reservation_status` sea `approved` no se
	# serializa. Ver `restaurants/services/reservations.py`.
	reservation_url = models.URLField(
		max_length=500,
		blank=True,
		# El default de Django acepta ftp y ftps. Acá el valor termina en un
		# botón que abre el navegador del usuario: sólo http(s).
		validators=[URLValidator(schemes=["http", "https"])],
	)
	reservation_provider = models.CharField(
		max_length=20,
		choices=ReservationProvider.choices,
		blank=True,
	)
	reservation_status = models.CharField(
		max_length=10,
		choices=ReservationStatus.choices,
		default=ReservationStatus.PENDING,
		db_index=True,
	)
	phone = models.CharField(max_length=30, blank=True)
	google_place_id = models.CharField(max_length=255, blank=True, unique=True, null=True)
	opening_hours = models.JSONField(default=list, blank=True)
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
		# Required, not cosmetic: the list endpoint paginates, and paginating an
		# unordered queryset lets PostgreSQL return rows in any order it likes —
		# so the same row could appear on two pages, or on none. Name over
		# created_at because this is a catalogue people browse, and `id` breaks
		# the tie so the order is total.
		ordering = ["name", "id"]

	# Valor de `reservation_url` tal como salió de la base. `None` significa
	# "esta instancia no vino de la base", o sea que la URL es nueva y hay
	# que clasificarla. Sin este snapshot habría que elegir entre
	# reclasificar en cada save —pisando la aprobación manual del admin en el
	# guardado siguiente— o no reclasificar nunca, que deja pasar una URL
	# nueva sin revisar.
	_reservation_url_at_load = None

	@classmethod
	def from_db(cls, db, field_names, values):
		instance = super().from_db(db, field_names, values)
		instance._reservation_url_at_load = instance.reservation_url
		return instance

	def save(self, *args, **kwargs):
		"""Clasifica la URL de reserva cuando cambió.

		Va en el modelo y no en el serializer —contra la regla general del
		proyecto— porque este campo entra por tres puertas: la API, el admin
		y el importador. Es derivación de campos, no validación de entrada:
		la validación de que sea http(s) sigue levantando ValidationError.
		"""
		from restaurants.services.reservations import classify_reservation_url

		changed = (
			self._reservation_url_at_load is None
			or self.reservation_url != self._reservation_url_at_load
		)
		if changed:
			if self.reservation_url:
				result = classify_reservation_url(
					self.reservation_url, name=self.name, website=self.website
				)
				self.reservation_provider = result.provider
				self.reservation_status = result.status
			else:
				self.reservation_provider = ""
				self.reservation_status = self.ReservationStatus.PENDING

		super().save(*args, **kwargs)
		self._reservation_url_at_load = self.reservation_url

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
	# Dietary flags / "recommended" are now Tag M2M rows. Seeded slugs:
	# 'vegetarian', 'gluten-free' (kind=dietary), 'recommended' (kind=highlight).
	# Adding a new flag = create a Tag, no migration. See migration 0011.
	tags = models.ManyToManyField(Tag, blank=True, related_name="menu_items")
	image_url = models.URLField(max_length=2000, blank=True)

	class Meta:
		db_table = "restaurants_menu_item"
		ordering = ["category", "name"]

	def __str__(self):
		return f"{self.name} — {self.restaurant.name}"
