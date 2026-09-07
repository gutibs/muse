"""El endpoint que le dice a la app si puede seguir funcionando.

Existe por un caso real: el 2026-09-06, probando la V1.3.0, el teléfono tenía
instalada la V1.2.0 —de antes de que cambiara el contrato del registro— y la app
vieja arrancaba igual y fallaba en la cara del usuario, sin decir por qué.

**Todo el diseño es "falla abierto".** Un chequeo de versión que falla cerrado
convierte cualquier caída del backend en todas las apps del mundo bloqueadas,
que es peor que el problema que resuelve. Por eso una plataforma sin fila no
devuelve un error: devuelve una política que no bloquea a nadie.
"""

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from releases.models import AppVersion


@pytest.fixture
def client():
	return APIClient()


@pytest.fixture
def android():
	"""`update_or_create` y no `create`: la fila de android ya existe.

	La siembra `releases/0002_politica_inicial`, y las data migrations corren
	también en la base de test. Con `create` esto explota con una
	UniqueViolation que no tiene nada que ver con lo que el test prueba.
	"""
	obj, _ = AppVersion.objects.update_or_create(
		platform=AppVersion.Platform.ANDROID,
		defaults={
			"min_supported": "1.3.0",
			"latest": "1.4.1",
			"store_url": "https://lovemuse.app/download",
		},
	)
	return obj


@pytest.mark.critical
@pytest.mark.django_db
def test_lo_puede_leer_una_app_sin_sesion(client, android):
	"""Se consulta al arrancar, antes de cualquier login."""
	res = client.get(reverse("app-version"), {"platform": "android"})
	assert res.status_code == 200


@pytest.mark.django_db
def test_devuelve_las_dos_versiones_y_a_donde_mandar(client, android):
	res = client.get(reverse("app-version"), {"platform": "android"})
	assert res.data["minSupported"] == "1.3.0"
	assert res.data["latest"] == "1.4.1"
	assert res.data["storeUrl"] == "https://lovemuse.app/download"


@pytest.mark.critical
@pytest.mark.django_db
def test_una_plataforma_sin_configurar_no_bloquea_a_nadie(client):
	"""El caso que no puede devolver 404 ni 500.

	iOS todavía no existe en la tabla. Si esto respondiera con un error, la app
	tendría que interpretar el error —y cualquier interpretación que bloquee
	deja a la gente afuera por una fila que falta en una tabla.
	"""
	res = client.get(reverse("app-version"), {"platform": "ios"})
	assert res.status_code == 200
	assert res.data["minSupported"] == "0.0.0"


@pytest.mark.critical
@pytest.mark.django_db
def test_sin_plataforma_tampoco_rompe(client, android):
	"""Un APK viejo que algún día llame sin el parámetro tiene que entrar."""
	res = client.get(reverse("app-version"))
	assert res.status_code == 200
	assert res.data["minSupported"] == "0.0.0"


@pytest.mark.django_db
def test_una_plataforma_inventada_se_comporta_como_las_demas(client):
	res = client.get(reverse("app-version"), {"platform": "carrier-pigeon"})
	assert res.status_code == 200
	assert res.data["minSupported"] == "0.0.0"


@pytest.mark.django_db
def test_no_expone_nada_mas_que_eso(client, android):
	"""Endpoint anónimo: lo que no se necesita, no se sirve."""
	assert set(res_keys(client)) == {"minSupported", "latest", "storeUrl"}


def res_keys(client):
	return client.get(reverse("app-version"), {"platform": "android"}).data.keys()


@pytest.mark.django_db
def test_solo_hay_una_politica_por_plataforma(android):
	"""Dos filas de android y cuál gana depende del orden de la query."""
	from django.db import IntegrityError

	with pytest.raises(IntegrityError):
		AppVersion.objects.create(
			platform=AppVersion.Platform.ANDROID, min_supported="9.9.9", latest="9.9.9"
		)


@pytest.mark.django_db
def test_el_piso_no_puede_ser_mayor_que_la_ultima(client):
	"""Un dedazo en el admin dejaría a todo el mundo bloqueado sin salida:
	nadie puede estar por encima de un piso que ni la última versión alcanza."""
	from django.core.exceptions import ValidationError

	v = AppVersion(platform=AppVersion.Platform.IOS, min_supported="2.0.0", latest="1.0.0")
	with pytest.raises(ValidationError):
		v.full_clean()
