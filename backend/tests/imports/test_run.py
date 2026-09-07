"""El despachador del import y la confirmación (F2.G).

Tercera pieza: junta el parseo con el matcheo y deja el job listo para que la
persona confirme. **Nada crea un pin hasta esa confirmación** — el match por
nombre acierta alto pero no perfecto, y un import a ciegas le llena la cuenta a
alguien con restaurantes equivocados.
"""

from unittest.mock import patch

import pytest
from django.contrib.gis.geos import Point

from imports.models import ImportJob
from imports.services.run import confirm_job, run_pending
from restaurants.models import Restaurant

pytestmark = pytest.mark.django_db


@pytest.fixture
def alguien(django_user_model):
	return django_user_model.objects.create_user(username="importa", password="x")


def _restaurante(nombre, ciudad=""):
	return Restaurant.objects.create(
		name=nombre,
		city=ciudad,
		location=Point(114.15, 22.28, srid=4326),
		approval_status=Restaurant.ApprovalStatus.APPROVED,
	)


def _job(alguien, filas):
	return ImportJob.objects.create(
		user=alguien,
		source="lista.csv",
		total=len(filas),
		report=[{**f, "outcome": "pending"} for f in filas],
	)


def test_el_despachador_resuelve_las_filas_y_deja_el_job_listo(alguien):
	_restaurante("Yardbird", "Hong Kong")
	job = _job(alguien, [{"row": 2, "name": "Yardbird", "city": "Hong Kong"}])

	with patch("imports.services.match.google_places"):
		stats = run_pending()

	job.refresh_from_db()
	assert job.state == ImportJob.State.READY
	assert job.matched == 1
	assert job.report[0]["outcome"] == "catalogue"
	assert job.report[0]["restaurant_id"]
	assert stats["jobs"] == 1


@pytest.mark.critical
def test_matchear_no_crea_ni_un_pin(alguien):
	"""La confirmación es obligatoria y esto lo fija.

	Sin esto, alguien sube un archivo con un nombre ambiguo y se encuentra la
	cuenta llena de lugares que no eligió.
	"""
	from pins.models import Pin

	_restaurante("Yardbird", "Hong Kong")
	_job(alguien, [{"row": 2, "name": "Yardbird", "city": "Hong Kong"}])

	with patch("imports.services.match.google_places"):
		run_pending()

	assert Pin.objects.count() == 0


def test_una_fila_rota_no_frena_las_demas(alguien):
	"""Un 502 en la fila 2 no puede dejar sin importar la 3."""
	from places.services.google_places import GooglePlacesError

	_restaurante("Anchoita", "Buenos Aires")
	job = _job(
		alguien,
		[
			{"row": 2, "name": "Explota", "city": ""},
			{"row": 3, "name": "Anchoita", "city": "Buenos Aires"},
		],
	)

	with patch("imports.services.match.google_places") as google:
		google.autocomplete.side_effect = GooglePlacesError("502")
		run_pending()

	job.refresh_from_db()
	assert job.state == ImportJob.State.READY
	assert job.matched == 1
	assert job.failed == 1
	assert {f["outcome"] for f in job.report} == {"error", "catalogue"}


def test_la_confirmacion_crea_los_pins_de_lo_elegido(alguien):
	from pins.models import Pin

	uno = _restaurante("Yardbird", "Hong Kong")
	otro = _restaurante("Anchoita", "Buenos Aires")
	job = ImportJob.objects.create(
		user=alguien,
		state=ImportJob.State.READY,
		total=2,
		matched=2,
		report=[
			{"row": 2, "name": "Yardbird", "outcome": "catalogue", "restaurant_id": uno.pk},
			{"row": 3, "name": "Anchoita", "outcome": "catalogue", "restaurant_id": otro.pk},
		],
	)

	creados = confirm_job(job, [uno.pk])

	assert creados == 1
	assert Pin.objects.count() == 1
	pin = Pin.objects.get()
	assert pin.restaurant == uno
	assert pin.status == Pin.Status.TO_VISIT
	# `to_visit` no lleva rating: es la regla que ya valida el serializer.
	assert pin.rating is None
	job.refresh_from_db()
	assert job.state == ImportJob.State.CONFIRMED


@pytest.mark.critical
def test_no_se_puede_confirmar_un_restaurante_que_no_estaba_en_el_reporte(alguien):
	"""El id viene del cliente: sin este corte, cualquiera se pinea lo que
	quiera mandando ids que nunca salieron de su archivo."""
	from pins.models import Pin

	suyo = _restaurante("Yardbird", "Hong Kong")
	ajeno = _restaurante("Otro lugar", "Roma")
	job = ImportJob.objects.create(
		user=alguien,
		state=ImportJob.State.READY,
		total=1,
		matched=1,
		report=[{"row": 2, "name": "Yardbird", "outcome": "catalogue", "restaurant_id": suyo.pk}],
	)

	creados = confirm_job(job, [suyo.pk, ajeno.pk])

	assert creados == 1
	assert Pin.objects.count() == 1
	assert Pin.objects.get().restaurant == suyo


def test_confirmar_algo_que_ya_estaba_pineado_no_duplica(alguien):
	"""Pinear dos veces el mismo lugar da 409 por API; acá simplemente se
	saltea, porque la persona no eligió pinearlo dos veces."""
	from pins.models import Pin

	lugar = _restaurante("Yardbird", "Hong Kong")
	Pin.objects.create(user=alguien, restaurant=lugar, status=Pin.Status.VISITED, rating=4)
	job = ImportJob.objects.create(
		user=alguien,
		state=ImportJob.State.READY,
		total=1,
		matched=1,
		report=[{"row": 2, "name": "Yardbird", "outcome": "catalogue", "restaurant_id": lugar.pk}],
	)

	creados = confirm_job(job, [lugar.pk])

	assert creados == 0
	assert Pin.objects.count() == 1
	assert Pin.objects.get().status == Pin.Status.VISITED


def test_un_job_ya_confirmado_no_se_confirma_de_nuevo(alguien):
	from pins.models import Pin

	lugar = _restaurante("Yardbird", "Hong Kong")
	job = ImportJob.objects.create(
		user=alguien,
		state=ImportJob.State.CONFIRMED,
		total=1,
		report=[{"row": 2, "name": "Yardbird", "outcome": "catalogue", "restaurant_id": lugar.pk}],
	)

	assert confirm_job(job, [lugar.pk]) == 0
	assert Pin.objects.count() == 0
