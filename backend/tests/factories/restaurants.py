import factory
from django.contrib.gis.geos import Point
from django.utils.text import slugify

from restaurants.models import Cuisine, Restaurant
from tests.factories.base import BaseFactory


class CuisineFactory(BaseFactory):
	class Meta:
		model = Cuisine
		django_get_or_create = ("slug",)

	name = factory.Sequence(lambda n: f"Cuisine {n}")
	slug = factory.LazyAttribute(lambda o: slugify(o.name))


class RestaurantFactory(BaseFactory):
	class Meta:
		model = Restaurant

	name = factory.Sequence(lambda n: f"Restaurant {n}")
	location = factory.LazyFunction(lambda: Point(-58.38, -34.60, srid=4326))
	approval_status = Restaurant.ApprovalStatus.APPROVED
	city = "Buenos Aires"
	country = "Argentina"
