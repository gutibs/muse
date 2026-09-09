"""Resolver cada fila del archivo a un restaurante (F2.G).

**El orden de los tres saltos es lo que cuida la cuota**, y por eso es lo que
más se testea acá. Google da 1.000 llamadas gratis por SKU y por mes, y cada
fila que llega hasta allá cuesta dos: una de autocomplete para conseguir el
`place_id` y otra de details para traer el lugar. Un import de 200 filas sin
mirar antes el catálogo se come el 40% del cupo mensual.

Por eso: primero el catálogo local, después la caché de places, y sólo entonces
Google. A medida que el catálogo crece, el costo de cada import baja solo.

Los mocks van al boundary externo —`google_places`— y no a internals del
service, como el resto de la suite.
"""

from unittest.mock import patch

import pytest
from django.contrib.gis.geos import Point

from imports.services.match import MatchOutcome, match_row
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


@pytest.mark.critical
def test_lo_que_ya_esta_en_el_catalogo_no_le_pregunta_a_google(alguien):
	"""El salto que hace que el importador no sea caro.

	Con el catálogo creciendo, cada import gasta menos que el anterior. Si esto
	se rompe, no falla nada: sólo se empieza a pagar por lugares que ya
	teníamos, y eso no se nota hasta que llega la factura.
	"""
	esperado = _restaurante("Yardbird", "Hong Kong")

	with patch("imports.services.match.google_places") as google:
		resultado = match_row({"name": "Yardbird", "city": "Hong Kong", "row": 2}, alguien)

	assert resultado.outcome == MatchOutcome.CATALOGUE
	assert resultado.restaurant == esperado
	google.autocomplete.assert_not_called()


def test_el_match_local_no_distingue_mayusculas_ni_espacios(alguien):
	esperado = _restaurante("Yardbird", "Hong Kong")

	with patch("imports.services.match.google_places") as google:
		resultado = match_row({"name": "  yardbird ", "city": "hong kong", "row": 2}, alguien)

	assert resultado.restaurant == esperado
	google.autocomplete.assert_not_called()


def test_la_ciudad_desambigua_dos_lugares_del_mismo_nombre(alguien):
	_restaurante("La Rosa", "Roma")
	porteño = _restaurante("La Rosa", "Buenos Aires")

	with patch("imports.services.match.google_places"):
		resultado = match_row({"name": "La Rosa", "city": "Buenos Aires", "row": 2}, alguien)

	assert resultado.restaurant == porteño


@pytest.mark.critical
def test_sin_ciudad_y_con_dos_candidatos_no_adivina(alguien):
	"""Elegir uno al azar mete en la cuenta de alguien el restaurante
	equivocado, en otro continente, sin que se entere."""
	_restaurante("La Rosa", "Roma")
	_restaurante("La Rosa", "Buenos Aires")

	with patch("imports.services.match.google_places") as google:
		google.autocomplete.return_value = []
		resultado = match_row({"name": "La Rosa", "city": "", "row": 2}, alguien)

	assert resultado.outcome == MatchOutcome.AMBIGUOUS
	assert resultado.restaurant is None


def test_lo_que_no_esta_se_busca_en_google_y_se_importa(alguien):
	# El restaurante NO existe antes: lo trae el importador, que es lo que este
	# test comprueba. Crearlo de antemano haría que lo encuentre el catálogo y
	# el test pasaría por el camino equivocado.
	def trae_de_google(place_id, user):
		return _restaurante("Nuevo", "Hong Kong"), True

	with patch("imports.services.match.google_places") as google:
		google.autocomplete.return_value = [{"placeId": "ChIJ_nuevo"}]
		with patch(
			"imports.services.match.import_from_google_place_id", side_effect=trae_de_google
		) as importar:
			resultado = match_row({"name": "Nuevo", "city": "Hong Kong", "row": 2}, alguien)

	assert resultado.outcome == MatchOutcome.IMPORTED
	assert resultado.restaurant.name == "Nuevo"
	importar.assert_called_once()
	assert importar.call_args.args[0] == "ChIJ_nuevo"


def test_si_google_no_conoce_el_lugar_la_fila_queda_sin_match(alguien):
	with patch("imports.services.match.google_places") as google:
		google.autocomplete.return_value = []
		resultado = match_row({"name": "No existe", "city": "", "row": 2}, alguien)

	assert resultado.outcome == MatchOutcome.NOT_FOUND
	assert resultado.restaurant is None


@pytest.mark.critical
def test_un_error_de_google_no_tumba_la_fila_entera_del_archivo(alguien):
	"""Cada fila falla sola: un 502 en la number 12 no puede cancelar las 200.

	Es la misma lección que el `render()` fuera del try en F2.E, donde un tipo
	sin texto bloqueaba todo lo que venía detrás.
	"""
	from places.services.google_places import GooglePlacesError

	with patch("imports.services.match.google_places") as google:
		google.autocomplete.side_effect = GooglePlacesError("502 de Google")
		resultado = match_row({"name": "Lo que sea", "city": "", "row": 12}, alguien)

	assert resultado.outcome == MatchOutcome.ERROR
	assert resultado.restaurant is None
	assert "502" in resultado.detail


def test_un_lugar_cerrado_no_se_ofrece(alguien):
	"""`from_google` ya corta los cerrados; el importador tiene que hacer lo
	mismo en vez de meterlos en la lista de alguien."""
	cerrado = _restaurante("Cerrado", "Hong Kong")
	cerrado.is_closed = True
	cerrado.save()

	with patch("imports.services.match.google_places") as google:
		google.autocomplete.return_value = []
		resultado = match_row({"name": "Cerrado", "city": "Hong Kong", "row": 2}, alguien)

	assert resultado.outcome != MatchOutcome.CATALOGUE
	assert resultado.restaurant is None


def test_dice_si_el_lugar_lo_dio_de_alta_este_import(alguien):
	# La distinción es la que decide quién puede describir el lugar: sólo el
	# import que lo trajo al catálogo, nunca el que se lo encontró ya hecho.
	def ya_existia(place_id, user):
		return _restaurante("Viejo", "Hong Kong"), False

	with patch("imports.services.match.google_places") as google:
		google.autocomplete.return_value = [{"placeId": "ChIJ_viejo"}]
		with patch("imports.services.match.import_from_google_place_id", side_effect=ya_existia):
			resultado = match_row({"name": "Otro nombre", "city": "Hong Kong", "row": 2}, alguien)

	assert resultado.outcome == MatchOutcome.IMPORTED
	assert resultado.created is False


def test_el_barrio_entra_en_la_busqueda_para_no_traer_otra_sucursal(alguien):
	# Hong Kong tiene el mismo local en Wan Chai y en Kowloon. Sin el barrio,
	# Google elige por popularidad y le mete a alguien la sucursal equivocada.
	def trae_de_google(place_id, user):
		return _restaurante("Samsen", "Hong Kong"), True

	with patch("imports.services.match.google_places") as google:
		google.autocomplete.return_value = [{"placeId": "ChIJ_samsen"}]
		with patch(
			"imports.services.match.import_from_google_place_id", side_effect=trae_de_google
		):
			match_row(
				{"name": "Samsen", "city": "Hong Kong", "district": "Wan Chai", "row": 2}, alguien
			)

	enviado = google.autocomplete.call_args.args[0]["input"]
	assert enviado == "Samsen Wan Chai Hong Kong"


def test_la_ciudad_matchea_aunque_el_catalogo_la_escriba_mas_larga(alguien):
	# Los 9 de Hong Kong que ya están cargados dicen "Hong Kong Island". Una
	# lista que dice "Hong Kong" —lo natural— los mandaría a Google a pagar dos
	# llamadas por cada uno para que vuelva el mismo lugar que ya teníamos.
	_restaurante("Duddell's", "Hong Kong Island")

	with patch("imports.services.match.google_places") as google:
		resultado = match_row({"name": "Duddell's", "city": "Hong Kong", "row": 2}, alguien)

	assert resultado.outcome == MatchOutcome.CATALOGUE
	google.autocomplete.assert_not_called()


def test_dos_ciudades_que_no_tienen_nada_que_ver_siguen_sin_matchear(alguien):
	_restaurante("Yardbird", "Tokyo")

	with patch("imports.services.match.google_places") as google:
		google.autocomplete.return_value = []
		resultado = match_row({"name": "Yardbird", "city": "Hong Kong", "row": 2}, alguien)

	assert resultado.outcome != MatchOutcome.CATALOGUE
