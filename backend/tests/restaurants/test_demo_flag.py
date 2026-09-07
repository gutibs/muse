"""El marcador de datos sembrados, y el comando que los borra.

Producción llegó a tener 500 restaurantes inventados de 557 —167 en Roma, 167
en Buenos Aires, 166 en Londres— sembrados por `seed_demo_restaurants` y
visibles en el catálogo como cualquier otro. El borrado estaba documentado como
una línea en un docstring y no existía en ningún lado.

**El invariante que importa acá es el de abajo, no el de arriba**: borrar los
sembrados no puede llevarse un lugar real ni el pin de otra persona sobre él.
`Pin.restaurant` es CASCADE, así que un filtro de más en la consulta de borrado
se lleva reseñas ajenas sin preguntar.
"""

import pytest
from django.contrib.gis.geos import Point
from django.core.management import call_command
from django.urls import reverse
from rest_framework.test import APIClient

from pins.models import Pin
from restaurants.models import Restaurant

pytestmark = pytest.mark.django_db


def _restaurante(nombre, *, demo=False, user=None):
	return Restaurant.objects.create(
		name=nombre,
		location=Point(-58.38, -34.60, srid=4326),
		approval_status=Restaurant.ApprovalStatus.APPROVED,
		is_demo=demo,
		created_by=user,
	)


@pytest.fixture
def alguien(django_user_model):
	return django_user_model.objects.create_user(username="real", password="x")


@pytest.mark.critical
def test_un_restaurante_de_demo_sigue_apareciendo_en_el_catalogo(alguien):
	"""**El flag no oculta nada**, y esto lo fija.

	Es lo contrario de `is_closed`, que sí filtra el listado, y por eso alguien
	va a "arreglarlo" por analogía en algún momento. La decisión fue explícita:
	el flag existe para poder borrarlos, no para esconderlos.
	"""
	_restaurante("Sembrado", demo=True)
	client = APIClient()
	client.force_authenticate(user=alguien)

	res = client.get(reverse("restaurant-list"))
	filas = res.data["results"] if "results" in res.data else res.data
	assert "Sembrado" in {f["name"] for f in filas}


def test_el_dry_run_no_borra_nada():
	_restaurante("Sembrado", demo=True)
	call_command("purge_demo_data", "--dry-run")
	assert Restaurant.objects.filter(is_demo=True).count() == 1


def test_sin_confirmar_tampoco_borra():
	"""El default seguro: sin `--yes` se comporta como un dry-run."""
	_restaurante("Sembrado", demo=True)
	call_command("purge_demo_data")
	assert Restaurant.objects.filter(is_demo=True).count() == 1


def test_borra_los_sembrados_y_sus_pins(alguien):
	sembrado = _restaurante("Sembrado", demo=True)
	Pin.objects.create(user=alguien, restaurant=sembrado, status=Pin.Status.TO_VISIT)

	call_command("purge_demo_data", "--yes")

	assert Restaurant.objects.filter(is_demo=True).count() == 0
	assert Pin.objects.count() == 0


@pytest.mark.critical
def test_no_toca_un_restaurante_real_ni_el_pin_de_nadie(alguien, django_user_model):
	"""El invariante que justifica el comando entero.

	`Pin.restaurant` es CASCADE: un filtro de más acá se lleva las reseñas de
	otra persona, que es exactamente lo que el comentario de `is_closed` en el
	modelo dice que no hay que provocar.
	"""
	otro = django_user_model.objects.create_user(username="otro", password="x")
	real = _restaurante("Anchoita")
	sembrado = _restaurante("Sembrado", demo=True)
	pin_ajeno = Pin.objects.create(user=otro, restaurant=real, status=Pin.Status.TO_VISIT)
	Pin.objects.create(user=alguien, restaurant=sembrado, status=Pin.Status.TO_VISIT)

	call_command("purge_demo_data", "--yes")

	assert Restaurant.objects.filter(pk=real.pk).exists()
	assert Pin.objects.filter(pk=pin_ajeno.pk).exists()
	assert Pin.objects.count() == 1


def test_se_lleva_el_rastro_de_analytics(alguien):
	"""`MonthlyVenueStat` guarda el nombre copiado y el dashboard lo lee de ahí.

	Con `SET_NULL`, borrar el restaurante deja la fila con el nombre del
	sembrado para siempre y sin FK para volver a encontrarla. Por eso el
	comando limpia analytics **antes** del delete y en el mismo paso.
	"""
	from analytics.models import Event, MonthlyVenueStat

	sembrado = _restaurante("Sembrado", demo=True)
	real = _restaurante("Anchoita")

	MonthlyVenueStat.objects.create(
		restaurant=sembrado, restaurant_name="Sembrado", month="2026-09-01"
	)
	MonthlyVenueStat.objects.create(restaurant=real, restaurant_name="Anchoita", month="2026-09-01")
	Event.objects.create(user=alguien, name="restaurant_view", restaurant=sembrado)

	call_command("purge_demo_data", "--yes")

	assert MonthlyVenueStat.objects.count() == 1
	assert MonthlyVenueStat.objects.first().restaurant_name == "Anchoita"
	assert Event.objects.filter(restaurant__isnull=False).count() == 0
	assert Event.objects.count() == 0


def test_sin_nada_que_borrar_no_falla():
	call_command("purge_demo_data", "--yes")
	assert Restaurant.objects.count() == 0
