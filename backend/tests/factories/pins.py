import factory

from pins.models import Pin, SharedList
from tests.factories.base import BaseFactory
from tests.factories.restaurants import RestaurantFactory
from tests.factories.users import UserFactory


class PinFactory(BaseFactory):
	class Meta:
		model = Pin

	user = factory.SubFactory(UserFactory)
	restaurant = factory.SubFactory(RestaurantFactory)
	status = Pin.Status.TO_VISIT


class SharedListFactory(BaseFactory):
	class Meta:
		model = SharedList

	user = factory.SubFactory(UserFactory)
	title = factory.Sequence(lambda n: f"Shared List {n}")
	is_active = True
