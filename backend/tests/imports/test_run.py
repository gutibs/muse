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
from restaurants.models import Restaurant, Tag

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


@pytest.mark.critical
def test_una_fila_sin_nombre_no_se_manda_a_buscar(alguien):
	"""El parseo ya la marcó ilegible: volver a mirarla es gastar de más.

	Apareció mirando la pantalla: la fila vacía salía como "falló la búsqueda"
	en vez de "esa fila no tenía nombre", porque el despachador la mandaba a
	Google con el nombre en blanco. Dos daños: una llamada facturada por una
	fila que ya sabíamos rota, y el motivo real reemplazado por uno que
	confunde a quien lee el reporte.
	"""
	job = ImportJob.objects.create(
		user=alguien,
		source="lista.csv",
		total=1,
		report=[
			{"row": 2, "name": "Yardbird", "city": "Hong Kong", "outcome": "pending"},
			{"row": 3, "name": "", "city": "Roma", "outcome": "unreadable"},
		],
	)
	_restaurante("Yardbird", "Hong Kong")

	with patch("imports.services.match.google_places") as google:
		run_pending()

	job.refresh_from_db()
	ilegible = [f for f in job.report if f["row"] == 3][0]
	assert ilegible["outcome"] == "unreadable"
	google.autocomplete.assert_not_called()


def test_las_filas_ilegibles_cuentan_en_el_total(alguien):
	"""Si no, la pantalla dice "2 de 4" con tres problemas listados abajo."""
	job = ImportJob.objects.create(
		user=alguien,
		source="lista.csv",
		total=2,
		report=[
			{"row": 2, "name": "Yardbird", "city": "Hong Kong", "outcome": "pending"},
			{"row": 3, "name": "", "city": "Roma", "outcome": "unreadable"},
		],
	)
	_restaurante("Yardbird", "Hong Kong")

	with patch("imports.services.match.google_places"):
		run_pending()

	job.refresh_from_db()
	assert job.matched + job.failed == len(job.report)


@pytest.mark.critical
def test_el_import_describe_el_lugar_que_dio_de_alta(alguien):
	def trae_de_google(place_id, user):
		return _restaurante("Nuevo", "Hong Kong"), True

	job = _job(
		alguien,
		[{"row": 2, "name": "Nuevo", "city": "Hong Kong", "tags": ["romantic", "date-night"]}],
	)

	with patch("imports.services.match.google_places") as google:
		google.autocomplete.return_value = [{"placeId": "ChIJ_nuevo"}]
		with patch(
			"imports.services.match.import_from_google_place_id", side_effect=trae_de_google
		):
			run_pending()

	job.refresh_from_db()
	restaurante = Restaurant.objects.get(pk=job.report[0]["restaurant_id"])
	assert set(restaurante.tags.values_list("slug", flat=True)) == {"romantic", "date-night"}
	assert job.report[0]["tags"] == ["romantic", "date-night"]


@pytest.mark.critical
def test_un_import_no_pisa_las_etiquetas_que_puso_otro(alguien):
	# La regla de autoridad del catálogo: `_check_owner_or_staff` impide editar
	# un restaurante ajeno por la API, y el import no puede ser la puerta de
	# atrás de eso. Describir un lugar es dato compartido, no un pin propio.
	yardbird = _restaurante("Yardbird", "Hong Kong")
	yardbird.tags.add(Tag.objects.get(slug="trendy"))
	job = _job(alguien, [{"row": 2, "name": "Yardbird", "city": "Hong Kong", "tags": ["quiet"]}])

	with patch("imports.services.match.google_places"):
		run_pending()

	job.refresh_from_db()
	assert list(yardbird.tags.values_list("slug", flat=True)) == ["trendy"]
	assert job.report[0]["tags"] == []
	assert job.report[0]["tags_skipped"] == ["quiet"]


@pytest.mark.critical
def test_lo_que_google_infirio_no_cuenta_como_descrito(alguien):
	# `outdoor-terrace` la pone `google_import` sola cuando el payload dice que
	# hay terraza. Es un hecho del local, no el criterio de nadie: si contara
	# como "ya descrito", el backfill de atributos dejaría medio catálogo
	# bloqueado para siempre y sin que se note.
	limewood = _restaurante("Limewood", "Hong Kong")
	limewood.tags.add(Tag.objects.get(slug="outdoor-terrace"))
	_job(alguien, [{"row": 2, "name": "Limewood", "city": "Hong Kong", "tags": ["casual"]}])

	with patch("imports.services.match.google_places"):
		run_pending()

	assert set(limewood.tags.values_list("slug", flat=True)) == {"outdoor-terrace", "casual"}
