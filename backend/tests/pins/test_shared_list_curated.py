"""Listas curadas: elegir qué va y en qué orden.

Hasta ahora una lista compartida era un filtro sobre todos los pins del
dueño. "My top three" no es eso.

El default de `kind` es `auto` y no es negociable: con `curated` por defecto,
todo link ya compartido pasaría a mostrar cero restaurantes de golpe.
"""

import datetime as dt

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from pins.models import Pin, SharedList, SharedListItem
from pins.serializers_public import CURATED_ITEM_LIMIT
from tests.factories import PinFactory, RestaurantFactory, UserFactory


def _client(user):
	c = APIClient()
	c.force_authenticate(user=user)
	return c


@pytest.mark.critical
@pytest.mark.django_db
def test_an_existing_list_keeps_showing_everything():
	"""La migración no puede vaciar los links que ya circulan."""
	user = UserFactory()
	PinFactory(user=user, restaurant=RestaurantFactory())
	PinFactory(user=user, restaurant=RestaurantFactory())
	lista = SharedList.objects.create(user=user, title="Mis lugares")

	assert lista.kind == SharedList.Kind.AUTO

	resp = APIClient().get(reverse("shared-list-public", args=[lista.token]))

	assert resp.status_code == 200, resp.content
	assert len(resp.json()["pins"]) == 2


@pytest.mark.critical
@pytest.mark.django_db
def test_a_curated_list_shows_only_its_items_in_order():
	user = UserFactory()
	primero = PinFactory(user=user, restaurant=RestaurantFactory(name="Tercero"))
	segundo = PinFactory(user=user, restaurant=RestaurantFactory(name="Primero"))
	PinFactory(user=user, restaurant=RestaurantFactory(name="Fuera de la lista"))

	lista = SharedList.objects.create(user=user, title="Top 2", kind=SharedList.Kind.CURATED)
	SharedListItem.objects.create(shared_list=lista, pin=segundo, position=0)
	SharedListItem.objects.create(shared_list=lista, pin=primero, position=1)

	resp = APIClient().get(reverse("shared-list-public", args=[lista.token]))

	nombres = [p["restaurantDetail"]["name"] for p in resp.json()["pins"]]
	assert nombres == ["Primero", "Tercero"]


@pytest.mark.django_db
def test_an_item_can_carry_a_note():
	user = UserFactory()
	pin = PinFactory(user=user)
	lista = SharedList.objects.create(user=user, kind=SharedList.Kind.CURATED)
	SharedListItem.objects.create(shared_list=lista, pin=pin, position=0, note="Pedí el pulpo")

	resp = APIClient().get(reverse("shared-list-public", args=[lista.token]))

	assert resp.json()["pins"][0]["note"] == "Pedí el pulpo"


@pytest.mark.critical
@pytest.mark.django_db
def test_the_list_is_capped():
	"""El tope no es sólo de producto: acota lo que puede costar una sola
	request anónima."""
	user = UserFactory()
	pins = [
		PinFactory(user=user, restaurant=RestaurantFactory()) for _ in range(CURATED_ITEM_LIMIT + 1)
	]

	resp = _client(user).post(
		reverse("shared-list-list"),
		{"title": "Demasiados", "kind": "curated", "pinIds": [p.id for p in pins]},
		format="json",
	)

	assert resp.status_code == 400, resp.content
	assert SharedList.objects.count() == 0


@pytest.mark.critical
@pytest.mark.django_db
def test_you_cannot_curate_someone_elses_pin():
	ajeno = PinFactory(user=UserFactory())
	yo = UserFactory()

	resp = _client(yo).post(
		reverse("shared-list-list"),
		{"title": "Robada", "kind": "curated", "pinIds": [ajeno.id]},
		format="json",
	)

	assert resp.status_code == 400, resp.content
	assert SharedListItem.objects.count() == 0


@pytest.mark.django_db
def test_creating_a_curated_list_through_the_api():
	user = UserFactory()
	uno = PinFactory(user=user, restaurant=RestaurantFactory(name="Uno"))
	dos = PinFactory(user=user, restaurant=RestaurantFactory(name="Dos"))

	resp = _client(user).post(
		reverse("shared-list-list"),
		{"title": "Top 2", "kind": "curated", "pinIds": [dos.id, uno.id]},
		format="json",
	)

	assert resp.status_code == 201, resp.content
	lista = SharedList.objects.get()
	assert [i.pin_id for i in lista.items.order_by("position")] == [dos.id, uno.id]


@pytest.mark.django_db
def test_reordering_replaces_the_previous_selection():
	user = UserFactory()
	uno = PinFactory(user=user, restaurant=RestaurantFactory())
	dos = PinFactory(user=user, restaurant=RestaurantFactory())
	lista = SharedList.objects.create(user=user, kind=SharedList.Kind.CURATED)
	SharedListItem.objects.create(shared_list=lista, pin=uno, position=0)

	resp = _client(user).patch(
		reverse("shared-list-detail", args=[lista.id]),
		{"pinIds": [dos.id, uno.id]},
		format="json",
	)

	assert resp.status_code == 200, resp.content
	assert [i.pin_id for i in lista.items.order_by("position")] == [dos.id, uno.id]


@pytest.mark.critical
@pytest.mark.django_db
def test_an_expired_link_is_a_404():
	"""Una lista que se llamó "almuerzo del viernes" tiene vida útil de días,
	y hasta ahora el único apagador era acordarse de desactivarla."""
	user = UserFactory()
	PinFactory(user=user)
	lista = SharedList.objects.create(
		user=user, expires_at=timezone.now() - dt.timedelta(minutes=1)
	)

	resp = APIClient().get(reverse("shared-list-public", args=[lista.token]))

	assert resp.status_code == 404, resp.content


@pytest.mark.django_db
def test_a_link_that_has_not_expired_still_works():
	user = UserFactory()
	PinFactory(user=user)
	lista = SharedList.objects.create(user=user, expires_at=timezone.now() + dt.timedelta(days=1))

	resp = APIClient().get(reverse("shared-list-public", args=[lista.token]))

	assert resp.status_code == 200, resp.content


@pytest.mark.critical
@pytest.mark.django_db
def test_deleting_the_account_takes_the_curated_items_with_it():
	"""`account_deletion` borra las SharedList; los items tienen que irse con
	ellas y no quedar colgando."""
	from accounts.services.account_deletion import anonymise_user

	user = UserFactory()
	pin = PinFactory(user=user, status=Pin.Status.VISITED, rating=4)
	lista = SharedList.objects.create(user=user, kind=SharedList.Kind.CURATED)
	SharedListItem.objects.create(shared_list=lista, pin=pin, position=0)

	anonymise_user(user)

	assert SharedList.objects.count() == 0
	assert SharedListItem.objects.count() == 0
	# La reseña sobrevive, como manda D-009.
	assert Pin.objects.filter(pk=pin.pk).exists()
