"""El dashboard es la única superficie donde alguien lee estos números.

Lo mira la dueña del producto desde el admin. Los dos chequeos que importan:
que no sea público, y que muestre las dos cifras (deduplicada y bruta) para
que el número que se le muestra a un tercero se pueda explicar.
"""

from datetime import UTC, datetime

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from analytics.models import Event
from analytics.services.ingest import record_event
from tests.factories import RestaurantFactory, UserFactory


@pytest.mark.critical
@pytest.mark.django_db
def test_the_dashboard_is_not_public():
	url = reverse("admin:analytics_dashboard")

	resp = APIClient().get(url)

	assert resp.status_code in (302, 403), resp.status_code
	assert "/admin/login" in resp.get("Location", "/admin/login")


@pytest.mark.critical
@pytest.mark.django_db
def test_a_plain_user_cannot_open_it():
	user = UserFactory()
	client = APIClient()
	client.force_login(user)

	resp = client.get(reverse("admin:analytics_dashboard"))

	assert resp.status_code in (302, 403), resp.status_code


@pytest.mark.django_db
def test_staff_sees_both_the_deduped_and_the_raw_number(django_user_model):
	restaurant = RestaurantFactory(name="Bar Nacional")
	someone = UserFactory()
	for _ in range(3):
		record_event(
			name=Event.Name.EXTERNAL_ACTION_CLICK,
			user=someone,
			restaurant=restaurant,
			destination=Event.Destination.RESERVATION,
		)
	staff = django_user_model.objects.create_superuser(
		username="jess", email="jess@example.com", password="admin-pass-123"
	)
	client = APIClient()
	client.force_login(staff)

	resp = client.get(reverse("admin:analytics_dashboard"))

	assert resp.status_code == 200
	body = resp.content.decode()
	assert "Bar Nacional" in body
	# Tres taps de la misma persona el mismo día: 3 en bruto, 1 deduplicado.
	assert "<td>3</td>" in body
	assert "<td>1</td>" in body


@pytest.mark.django_db
def test_the_dashboard_holds_up_with_no_data(django_user_model):
	staff = django_user_model.objects.create_superuser(
		username="jess2", email="jess2@example.com", password="admin-pass-123"
	)
	client = APIClient()
	client.force_login(staff)

	resp = client.get(reverse("admin:analytics_dashboard"))

	assert resp.status_code == 200
	assert "No external clicks recorded yet." in resp.content.decode()


@pytest.mark.django_db
def test_an_event_of_a_deleted_restaurant_keeps_its_name_in_the_aggregate():
	"""El FK es SET_NULL: sin el nombre copiado en la fila del agregado, el
	histórico de un venue borrado quedaría sin dueño en el reporte."""
	from analytics.models import MonthlyVenueStat
	from analytics.services.reports import rollup_month

	restaurant = RestaurantFactory(name="Bar Nacional")
	record_event(
		name=Event.Name.EXTERNAL_ACTION_CLICK,
		user=UserFactory(),
		restaurant=restaurant,
		destination=Event.Destination.DIRECTIONS,
	)
	rollup_month(datetime.now(tz=UTC).date())

	restaurant.delete()

	stat = MonthlyVenueStat.objects.get()
	assert stat.restaurant_id is None
	assert stat.restaurant_name == "Bar Nacional"
