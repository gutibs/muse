"""El derecho de oposición (art. 21 GDPR) tiene que existir en el código.

La política publicada dice que si alguien se opone dejamos de registrar sus
eventos. Una política que promete algo que el código no hace es peor que no
prometerlo: es la parte del cumplimiento que un regulador puede verificar en
un minuto.
"""

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from analytics.models import Event
from analytics.services.ingest import record_event
from pins.models import Pin
from tests.factories import PinFactory, RestaurantFactory, UserFactory


@pytest.mark.critical
@pytest.mark.django_db
def test_an_objecting_user_generates_no_events_from_the_server():
	user = UserFactory()
	user.profile.analytics_opt_out = True
	user.profile.save()

	PinFactory(user=user, restaurant=RestaurantFactory(), status=Pin.Status.TO_VISIT)

	assert Event.objects.count() == 0


@pytest.mark.critical
@pytest.mark.django_db
def test_an_objecting_user_generates_no_events_from_the_client():
	user = UserFactory()
	user.profile.analytics_opt_out = True
	user.profile.save()
	client = APIClient()
	client.force_authenticate(user=user)

	resp = client.post(
		reverse("analytics-events"),
		{"events": [{"name": "venue_card_view", "restaurant": RestaurantFactory().id}]},
		format="json",
	)

	# El cliente no necesita enterarse: se acepta y se descarta. Devolver un
	# error obligaría a la app a manejar un caso que no es un fallo.
	assert resp.status_code == 201, resp.content
	assert Event.objects.count() == 0


@pytest.mark.critical
@pytest.mark.django_db
def test_the_user_can_object_through_their_profile():
	user = UserFactory()
	client = APIClient()
	client.force_authenticate(user=user)

	resp = client.patch(reverse("profile"), {"analyticsOptOut": True}, format="json")

	assert resp.status_code == 200, resp.content
	user.profile.refresh_from_db()
	assert user.profile.analytics_opt_out is True


@pytest.mark.django_db
def test_by_default_events_are_recorded():
	user = UserFactory()

	record_event(name=Event.Name.SAVE_TO_MAP, user=user, restaurant=RestaurantFactory())

	assert Event.objects.count() == 1
