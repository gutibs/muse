"""El filtro por ejes: OR adentro de cada uno, AND entre ellos (F2.C, RF1–RF6).

**El bug que estos tests existen para prevenir** es el AND silencioso. Los tres
ejes viven en la misma M2M distinguidos por `Tag.kind`, así que la forma
intuitiva —un solo `tags__slug__in=[...]` con todo adentro— compila, corre, no
falla y devuelve **de más**: se convierte en OR sin decirlo. Un filtro que
miente no se nota mirando la pantalla, porque los resultados de más se parecen
a los correctos.

El AND real necesita un join por eje. Eso es lo que fija
`test_dos_ejes_distintos_se_cruzan`.
"""

import pytest
from django.contrib.gis.geos import Point
from django.urls import reverse
from rest_framework.test import APIClient

from restaurants.models import Restaurant, Tag

pytestmark = pytest.mark.django_db


def _tag(slug, kind):
	obj, _ = Tag.objects.get_or_create(
		slug=slug, defaults={"name": slug.replace("-", " ").title(), "kind": kind}
	)
	return obj


def _restaurante(nombre, *slugs_kinds, user=None):
	r = Restaurant.objects.create(
		name=nombre,
		location=Point(-58.38, -34.60, srid=4326),
		approval_status=Restaurant.ApprovalStatus.APPROVED,
		created_by=user,
	)
	for slug, kind in slugs_kinds:
		r.tags.add(_tag(slug, kind))
	return r


@pytest.fixture
def client(django_user_model):
	user = django_user_model.objects.create_user(username="filtra", password="x")
	c = APIClient()
	c.force_authenticate(user=user)
	return c


def _nombres(res):
	datos = res.data
	filas = datos["results"] if isinstance(datos, dict) and "results" in datos else datos
	return {f["name"] for f in filas}


@pytest.fixture
def catalogo():
	"""Tres lugares elegidos para que el OR encubierto se note.

	`Solo Romantico` tiene el vibe pero no la ocasión: es el que aparece de más
	cuando el AND está mal hecho.
	"""
	_restaurante("Los Dos", ("romantic", Tag.Kind.VIBE), ("date-night", Tag.Kind.OCCASION))
	_restaurante("Solo Romantico", ("romantic", Tag.Kind.VIBE))
	_restaurante("Solo Cita", ("date-night", Tag.Kind.OCCASION))
	_restaurante("Ninguno", ("casual", Tag.Kind.VIBE))


def test_un_eje_filtra(client, catalogo):
	res = client.get(reverse("restaurant-list"), {"vibe": "romantic"})
	assert _nombres(res) == {"Los Dos", "Solo Romantico"}


def test_dentro_de_un_eje_los_valores_son_or(client, catalogo):
	res = client.get(reverse("restaurant-list"), {"vibe": "romantic,casual"})
	assert _nombres(res) == {"Los Dos", "Solo Romantico", "Ninguno"}


@pytest.mark.critical
def test_dos_ejes_distintos_se_cruzan(client, catalogo):
	"""El test que atrapa el OR encubierto.

	Con un solo `tags__slug__in` esto devolvería los tres primeros. El AND real
	deja únicamente al que tiene las dos etiquetas.
	"""
	res = client.get(reverse("restaurant-list"), {"vibe": "romantic", "occasion": "date-night"})
	assert _nombres(res) == {"Los Dos"}


@pytest.mark.critical
def test_los_cuatro_ejes_se_cruzan_entre_si(client):
	_restaurante(
		"Completo",
		("quiet", Tag.Kind.VIBE),
		("business-lunch", Tag.Kind.OCCASION),
		("outdoor-terrace", Tag.Kind.SCENE),
		("vegetarian", Tag.Kind.DIETARY),
	)
	_restaurante(
		"Casi",
		("quiet", Tag.Kind.VIBE),
		("business-lunch", Tag.Kind.OCCASION),
		("outdoor-terrace", Tag.Kind.SCENE),
	)
	res = client.get(
		reverse("restaurant-list"),
		{
			"vibe": "quiet",
			"occasion": "business-lunch",
			"scene": "outdoor-terrace",
			"dietary": "vegetarian",
		},
	)
	assert _nombres(res) == {"Completo"}


def test_un_valor_que_no_existe_no_devuelve_todo(client, catalogo):
	"""Ni un error: cero resultados. Devolver la lista entera ante un slug
	desconocido es la otra forma de que el filtro mienta."""
	res = client.get(reverse("restaurant-list"), {"vibe": "no-existe"})
	assert res.status_code == 200
	assert _nombres(res) == set()


def test_el_mismo_restaurante_no_aparece_repetido(client):
	"""Los joins de un M2M duplican filas si falta el distinct."""
	_restaurante("Uno", ("romantic", Tag.Kind.VIBE), ("quiet", Tag.Kind.VIBE))
	res = client.get(reverse("restaurant-list"), {"vibe": "romantic,quiet"})
	filas = res.data["results"] if "results" in res.data else res.data
	assert len(filas) == 1


def test_se_combina_con_los_filtros_que_ya_existian(client):
	uno = _restaurante("Con ciudad", ("romantic", Tag.Kind.VIBE))
	uno.city = "Hong Kong"
	uno.save()
	otro = _restaurante("Otra ciudad", ("romantic", Tag.Kind.VIBE))
	otro.city = "Buenos Aires"
	otro.save()

	res = client.get(reverse("restaurant-list"), {"vibe": "romantic", "city": "Hong Kong"})
	assert _nombres(res) == {"Con ciudad"}


def test_sin_parametros_no_filtra_nada(client, catalogo):
	res = client.get(reverse("restaurant-list"))
	assert len(_nombres(res)) == 4
