"""Borrar la cuenta no borra los eventos: los desidentifica.

Mismo invariante que las reseñas (D-009). Un evento es el rastro de que
alguien tocó "cómo llego" en un restaurante — el valor está en el conteo por
venue, no en quién fue. Borrarlos junto con la cuenta le sacaría meses de
historia al número que se le muestra a un tercero; conservarlos con el
user_id adentro contradiría el derecho de supresión. Se conserva la fila y
se pierde la identidad.

Que el FK sea SET_NULL no alcanza: la cuenta no se borra, se anonimiza, así
que el SET_NULL de la base nunca se dispara.
"""

import pytest

from accounts.services.account_deletion import anonymise_user
from analytics.models import Event
from analytics.services.ingest import record_event
from tests.factories import RestaurantFactory, UserFactory


@pytest.mark.critical
@pytest.mark.django_db
def test_deleting_an_account_keeps_the_events_without_the_user():
	user = UserFactory()
	restaurant = RestaurantFactory()
	record_event(name=Event.Name.SAVE_TO_MAP, user=user, restaurant=restaurant)
	record_event(
		name=Event.Name.EXTERNAL_ACTION_CLICK,
		user=user,
		restaurant=restaurant,
		destination=Event.Destination.DIRECTIONS,
	)

	anonymise_user(user)

	assert Event.objects.count() == 2
	assert Event.objects.filter(user__isnull=False).count() == 0
	assert Event.objects.filter(restaurant=restaurant).count() == 2


@pytest.mark.critical
@pytest.mark.django_db
def test_only_the_deleted_users_events_are_touched():
	leaving, staying = UserFactory(), UserFactory()
	restaurant = RestaurantFactory()
	record_event(name=Event.Name.SAVE_TO_MAP, user=leaving, restaurant=restaurant)
	record_event(name=Event.Name.SAVE_TO_MAP, user=staying, restaurant=restaurant)

	anonymise_user(leaving)

	assert Event.objects.filter(user=staying).count() == 1
	assert Event.objects.filter(user__isnull=True).count() == 1
