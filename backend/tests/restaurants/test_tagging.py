"""Traducir lo que alguien escribió en un archivo a etiquetas del catálogo.

Único lugar donde un texto suelto —"Date Night", "romantic", lo que sea que
haya tipeado la persona que armó la lista— se convierte en filas de `Tag`.
Vive en `restaurants/` y no en `imports/` porque `Restaurant.tags` es dominio
del catálogo: el día que la carga entre por un management command, la
traducción tiene que ser la misma.
"""

import pytest

from restaurants.services.tagging import apply_tags
from tests.factories.restaurants import RestaurantFactory

pytestmark = pytest.mark.django_db


def test_aplica_las_etiquetas_que_existen():
	# `trendy` lo siembra la data migration: el vocabulario es el real, no uno
	# inventado para el test.
	restaurante = RestaurantFactory()

	aplicadas, desconocidas = apply_tags(restaurante, ["trendy"])

	assert aplicadas == ["trendy"]
	assert desconocidas == []
	assert list(restaurante.tags.values_list("slug", flat=True)) == ["trendy"]


def test_una_etiqueta_que_no_existe_se_reporta_y_no_rompe_las_demas():
	restaurante = RestaurantFactory()

	aplicadas, desconocidas = apply_tags(restaurante, ["romantic", "cheap-and-cheerful"])

	assert aplicadas == ["romantic"]
	assert desconocidas == ["cheap-and-cheerful"]
	assert list(restaurante.tags.values_list("slug", flat=True)) == ["romantic"]
