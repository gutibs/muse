"""La API del importador: subir, ver y confirmar (F2.G).

Lo que se prueba acá y no en los otros archivos es el borde HTTP: que el archivo
se parsee al subir —para que la persona sepa al instante si sirve—, y sobre todo
**que nadie vea ni confirme el import de otra persona**.
"""

import io

import pytest
from django.contrib.gis.geos import Point
from django.urls import reverse
from rest_framework.test import APIClient

from imports.models import ImportJob
from restaurants.models import Restaurant

pytestmark = pytest.mark.django_db


def _archivo(texto="name,city\nYardbird,Hong Kong\n", nombre="lista.csv"):
	archivo = io.BytesIO(texto.encode("utf-8"))
	archivo.name = nombre
	return archivo


@pytest.fixture
def alguien(django_user_model):
	return django_user_model.objects.create_user(username="importa", password="x")


@pytest.fixture
def client(alguien):
	c = APIClient()
	c.force_authenticate(user=alguien)
	return c


def test_subir_un_archivo_crea_el_job_y_cuenta_las_filas(client):
	res = client.post(reverse("import-list"), {"file": _archivo()}, format="multipart")
	assert res.status_code == 201
	assert res.data["total"] == 1
	assert res.data["state"] == "pending"


def test_el_archivo_se_valida_al_subirlo_y_no_despues(client):
	"""Sin columna de nombre no hay nada que buscar: se avisa al instante, sin
	dejar a la persona esperando un job que iba a fallar igual."""
	res = client.post(
		reverse("import-list"),
		{"file": _archivo("telefono,direccion\n123,Calle 1\n")},
		format="multipart",
	)
	assert res.status_code == 400
	assert ImportJob.objects.count() == 0


def test_sin_archivo_avisa(client):
	assert client.post(reverse("import-list"), {}, format="multipart").status_code == 400


def test_las_filas_rotas_viajan_desde_el_principio(client):
	"""No hay que esperar el matcheo para saber que la fila 3 no tenía nombre."""
	res = client.post(
		reverse("import-list"),
		{"file": _archivo("name,city\nYardbird,Hong Kong\n,Roma\n")},
		format="multipart",
	)
	assert res.data["total"] == 1
	assert any(f["outcome"] == "unreadable" for f in res.data["report"])


@pytest.mark.critical
def test_nadie_ve_el_import_de_otra_persona(client, django_user_model):
	otro = django_user_model.objects.create_user(username="otro", password="x")
	ajeno = ImportJob.objects.create(user=otro, source="secreto.csv", total=1)

	assert client.get(reverse("import-detail", args=[ajeno.pk])).status_code == 404
	assert client.get(reverse("import-list")).data == []


@pytest.mark.critical
def test_nadie_confirma_el_import_de_otra_persona(client, django_user_model):
	from pins.models import Pin

	otro = django_user_model.objects.create_user(username="otro", password="x")
	lugar = Restaurant.objects.create(
		name="Yardbird",
		location=Point(114.15, 22.28, srid=4326),
		approval_status=Restaurant.ApprovalStatus.APPROVED,
	)
	ajeno = ImportJob.objects.create(
		user=otro,
		state=ImportJob.State.READY,
		total=1,
		report=[{"row": 2, "name": "Yardbird", "outcome": "catalogue", "restaurant_id": lugar.pk}],
	)

	res = client.post(
		reverse("import-confirm", args=[ajeno.pk]),
		{"restaurantIds": [lugar.pk]},
		format="json",
	)
	assert res.status_code == 404
	assert Pin.objects.count() == 0


def test_confirmar_crea_los_pins_y_lo_dice(client, alguien):
	from pins.models import Pin

	lugar = Restaurant.objects.create(
		name="Yardbird",
		location=Point(114.15, 22.28, srid=4326),
		approval_status=Restaurant.ApprovalStatus.APPROVED,
	)
	job = ImportJob.objects.create(
		user=alguien,
		state=ImportJob.State.READY,
		total=1,
		matched=1,
		report=[{"row": 2, "name": "Yardbird", "outcome": "catalogue", "restaurant_id": lugar.pk}],
	)

	res = client.post(
		reverse("import-confirm", args=[job.pk]),
		{"restaurantIds": [lugar.pk]},
		format="json",
	)
	assert res.status_code == 200
	assert res.data["created"] == 1
	assert Pin.objects.filter(user=alguien, restaurant=lugar).exists()


def test_hay_que_estar_logueado():
	anonimo = APIClient()
	assert anonimo.get(reverse("import-list")).status_code == 401
