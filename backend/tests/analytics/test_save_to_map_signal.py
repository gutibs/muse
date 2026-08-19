"""`save_to_map` se cuenta del lado del servidor.

Es el número que responde "cuánta gente guardó este restaurante", y el
endpoint de ingesta lo rechaza justamente para que no haya dos caminos. La
fuente es una sola: el Pin quedó creado en la base.
"""

import pytest

from analytics.models import Event
from pins.models import Pin
from tests.factories import PinFactory, RestaurantFactory, UserFactory


@pytest.mark.critical
@pytest.mark.django_db
def test_creating_a_pin_records_the_event():
	user = UserFactory()
	restaurant = RestaurantFactory()

	pin = PinFactory(user=user, restaurant=restaurant, status=Pin.Status.TO_VISIT)

	event = Event.objects.get(name=Event.Name.SAVE_TO_MAP)
	assert event.user_id == user.id
	assert event.restaurant_id == restaurant.id
	assert event.props == {"status": pin.status}


@pytest.mark.django_db
def test_editing_a_pin_does_not_record_another_save():
	"""Guardar es un hecho puntual. Si cada edición contara, corregir la
	reseña tres veces inflaría el número por tres."""
	pin = PinFactory(status=Pin.Status.TO_VISIT)
	Event.objects.all().delete()

	pin.status = Pin.Status.VISITED
	pin.rating = 4
	pin.save()

	assert Event.objects.filter(name=Event.Name.SAVE_TO_MAP).count() == 0


@pytest.mark.django_db
def test_unpinning_keeps_the_event():
	"""El evento sobrevive al despineo, con su restaurante intacto. Es
	exactamente lo que `feed.Activity` no puede hacer: su FK al Pin es
	CASCADE, así que el historial se borraría con el pin."""
	pin = PinFactory()
	restaurant_id = pin.restaurant_id

	pin.delete()

	event = Event.objects.get(name=Event.Name.SAVE_TO_MAP)
	assert event.restaurant_id == restaurant_id
