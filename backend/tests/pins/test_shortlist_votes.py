"""Votación en shortlists: el primer endpoint de escritura anónimo del proyecto.

Todo el resto del modelo de amenazas asume que escribir requiere JWT. Acá no
hay usuario contra el cual filtrar, así que el control de acceso es la lista
misma: el token tiene que existir, estar viva, ser curada y tener la votación
encendida por su dueño, y el item tiene que pertenecer a ESA lista.

Por eso los tests entran por la URL sin autenticar y observan por la misma
puerta: es exactamente lo que ve alguien que recibió el link por un chat.
"""

import datetime as dt
import uuid

import pytest
from django.core.cache import cache
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework.throttling import SimpleRateThrottle

from pins.models import SharedList, SharedListItem, ShortlistVote
from tests.factories import PinFactory, RestaurantFactory, UserFactory


def _lista_con_items(cantidad=1, *, voting_enabled=True, **kwargs):
	"""Una shortlist curada con `cantidad` items, lista para votar."""
	owner = UserFactory()
	lista = SharedList.objects.create(
		user=owner,
		title="Girls lunch",
		kind=SharedList.Kind.CURATED,
		voting_enabled=voting_enabled,
		**kwargs,
	)
	items = [
		SharedListItem.objects.create(
			shared_list=lista,
			pin=PinFactory(user=owner, restaurant=RestaurantFactory()),
			position=i,
		)
		for i in range(cantidad)
	]
	return lista, items


def _votar(lista, item, clave):
	return APIClient().post(
		reverse("shortlist-votes", args=[lista.token]),
		{"itemId": item.id},
		HTTP_X_MUSE_VOTER=str(clave),
	)


def _ver(lista):
	return APIClient().get(reverse("shared-list-public", args=[lista.token]))


@pytest.mark.critical
@pytest.mark.django_db
def test_un_voto_anonimo_se_cuenta_en_la_pagina_publica():
	lista, (item,) = _lista_con_items()

	resp = _votar(lista, item, uuid.uuid4())

	assert resp.status_code == 201, resp.content

	pagina = _ver(lista)
	assert pagina.status_code == 200, pagina.content
	assert pagina.json()["pins"][0]["voteCount"] == 1


@pytest.mark.critical
@pytest.mark.django_db
def test_la_misma_clave_dos_veces_deja_un_solo_voto():
	"""Un reintento por red inestable no puede duplicar el conteo.

	El endpoint es idempotente a propósito: repetir el POST es la operación
	normal de un cliente que no sabe si el primero llegó.
	"""
	lista, (item,) = _lista_con_items()
	clave = uuid.uuid4()

	primera = _votar(lista, item, clave)
	segunda = _votar(lista, item, clave)

	assert primera.status_code == 201, primera.content
	assert segunda.status_code == 200, segunda.content
	assert _ver(lista).json()["pins"][0]["voteCount"] == 1


@pytest.mark.critical
@pytest.mark.django_db
def test_sin_el_opt_in_del_dueno_no_se_puede_votar():
	"""Los links curados que ya circulan no se convierten en encuestas.

	404 y no 403: quien tiene el link no tiene por qué saber si la lista
	existe, igual que en el resto de esta superficie.
	"""
	lista, (item,) = _lista_con_items(voting_enabled=False)

	resp = _votar(lista, item, uuid.uuid4())

	assert resp.status_code == 404, resp.content


@pytest.mark.critical
@pytest.mark.django_db
def test_una_lista_auto_no_admite_votos():
	"""Votar es elegir entre lo que alguien eligió a mano.

	Una lista `auto` es un filtro sobre todos los pins del dueño; no tiene
	items, así que no hay nada sobre lo que votar.
	"""
	owner = UserFactory()
	auto = SharedList.objects.create(
		user=owner,
		title="Todo lo mío",
		kind=SharedList.Kind.AUTO,
		voting_enabled=True,
	)
	# El item cuelga de la lista `auto` misma: nada en el modelo impide
	# crearlo, y si el test usara un item de otra lista estaría probando el
	# filtro de pertenencia en vez del `kind`.
	item = SharedListItem.objects.create(
		shared_list=auto,
		pin=PinFactory(user=owner, restaurant=RestaurantFactory()),
	)

	resp = _votar(auto, item, uuid.uuid4())

	assert resp.status_code == 404, resp.content


@pytest.mark.django_db
def test_una_lista_apagada_o_vencida_no_admite_votos():
	apagada, (item_apagado,) = _lista_con_items(is_active=False)
	vencida, (item_vencido,) = _lista_con_items(expires_at=timezone.now() - dt.timedelta(hours=1))

	assert _votar(apagada, item_apagado, uuid.uuid4()).status_code == 404
	assert _votar(vencida, item_vencido, uuid.uuid4()).status_code == 404


def _desvotar(lista, item, clave):
	return APIClient().delete(
		reverse("shortlist-vote-detail", args=[lista.token, item.id]),
		HTTP_X_MUSE_VOTER=str(clave),
	)


@pytest.mark.django_db
def test_se_puede_sacar_el_voto():
	lista, (item,) = _lista_con_items()
	clave = uuid.uuid4()
	_votar(lista, item, clave)

	resp = _desvotar(lista, item, clave)

	assert resp.status_code == 204, resp.content
	assert _ver(lista).json()["pins"][0]["voteCount"] == 0


@pytest.mark.django_db
def test_sacar_un_voto_que_no_existe_tambien_da_204():
	"""Idempotente por la misma razón que el POST: el cliente reintenta."""
	lista, (item,) = _lista_con_items()

	resp = _desvotar(lista, item, uuid.uuid4())

	assert resp.status_code == 204, resp.content


@pytest.mark.django_db
def test_sacar_el_voto_no_toca_el_de_otra_persona():
	lista, (item,) = _lista_con_items()
	mia = uuid.uuid4()
	ajena = uuid.uuid4()
	_votar(lista, item, mia)
	_votar(lista, item, ajena)

	_desvotar(lista, item, mia)

	assert _ver(lista).json()["pins"][0]["voteCount"] == 1


@pytest.mark.django_db
def test_la_pagina_dice_si_se_vota_y_sobre_que_item():
	"""Sin el id del item, la página no tiene a qué apuntar el tick.

	`PublicPinSerializer` no expone el id del pin a propósito, así que el
	del item es el único identificador que viaja — y no sirve fuera de esta
	lista, porque la vista de votos valida la pertenencia.
	"""
	lista, (item,) = _lista_con_items()

	data = _ver(lista).json()

	assert data["votingEnabled"] is True
	assert data["pins"][0]["itemId"] == item.id


@pytest.mark.django_db
def test_una_lista_sin_votacion_no_anuncia_votos():
	lista, _ = _lista_con_items(voting_enabled=False)

	data = _ver(lista).json()

	assert data["votingEnabled"] is False


@pytest.mark.django_db
def test_la_pagina_dice_cuales_marco_quien_mira():
	"""El tick propio sale de la misma respuesta, no de una llamada aparte."""
	lista, (uno, otro) = _lista_con_items(2)
	clave = uuid.uuid4()
	_votar(lista, uno, clave)

	anonima = _ver(lista).json()["pins"]
	propia = (
		APIClient()
		.get(
			reverse("shared-list-public", args=[lista.token]),
			HTTP_X_MUSE_VOTER=str(clave),
		)
		.json()["pins"]
	)

	# Sin la clave no hay tick de nadie: la página se renderiza igual para
	# un buscador que para alguien que todavía no votó.
	assert [p["hasVoted"] for p in anonima] == [False, False]
	assert [p["hasVoted"] for p in propia] == [True, False]


@pytest.mark.critical
@pytest.mark.django_db
def test_una_clave_que_no_es_uuid_es_un_400_y_no_un_500():
	"""El header lo escribe un cliente que no controlamos.

	Si llega basura, la columna es un UUIDField y la consulta revienta con
	un 500 que además ensucia el log de errores con ruido de terceros.
	"""
	lista, (item,) = _lista_con_items()

	resp = APIClient().post(
		reverse("shortlist-votes", args=[lista.token]),
		{"itemId": item.id},
		HTTP_X_MUSE_VOTER="no-soy-un-uuid",
	)

	assert resp.status_code == 400, resp.content


@pytest.mark.critical
@pytest.mark.django_db
def test_sin_clave_de_votante_no_se_vota():
	lista, (item,) = _lista_con_items()

	resp = APIClient().post(
		reverse("shortlist-votes", args=[lista.token]),
		{"itemId": item.id},
	)

	assert resp.status_code == 400, resp.content
	assert _ver(lista).json()["pins"][0]["voteCount"] == 0


@pytest.mark.django_db
def test_una_clave_basura_al_mirar_no_rompe_la_pagina():
	"""Mirar no es votar: un header roto apaga los ticks, no la página."""
	lista, (item,) = _lista_con_items()
	_votar(lista, item, uuid.uuid4())

	resp = APIClient().get(
		reverse("shared-list-public", args=[lista.token]),
		HTTP_X_MUSE_VOTER="no-soy-un-uuid",
	)

	assert resp.status_code == 200, resp.content
	assert resp.json()["pins"][0]["voteCount"] == 1
	assert resp.json()["pins"][0]["hasVoted"] is False


@pytest.fixture
def con_throttle_de_votos(monkeypatch):
	"""La rate de votos bajada a 3, para no mandar 60 requests en un test.

	Se parchea `SimpleRateThrottle.THROTTLE_RATES` y **no** el setting:
	DRF evalúa `THROTTLE_RATES = api_settings.DEFAULT_THROTTLE_RATES` en el
	cuerpo de la clase, o sea una referencia al dict que había al importar el
	módulo. Reemplazar `settings.REST_FRAMEWORK` crea un dict nuevo que esa
	referencia nunca ve, así que el override tomaba efecto sólo si el import
	caía dentro del test — el mismo test pasaba solo y fallaba en la suite.

	Parte de las rates vigentes en vez de copiar la lista de scopes a mano:
	una copia se desactualiza en silencio y el test mide un límite que ya no
	existe.
	"""
	rates = {**SimpleRateThrottle.THROTTLE_RATES, "shortlist_vote": "3/hour"}
	monkeypatch.setattr(SimpleRateThrottle, "THROTTLE_RATES", rates)
	cache.clear()
	yield
	cache.clear()


@pytest.mark.critical
@pytest.mark.django_db
def test_el_conteo_no_se_infla_a_fuerza_de_claves_nuevas(con_throttle_de_votos):
	"""La única defensa contra el inflado es el throttle por IP.

	Una clave nueva por request es trivial de generar —el cliente la
	inventa— así que lo que tiene que frenar no es la clave repetida sino el
	volumen desde un mismo origen.
	"""
	lista, (item,) = _lista_con_items()

	codigos = [_votar(lista, item, uuid.uuid4()).status_code for _ in range(5)]

	assert 429 in codigos, f"ninguna request fue frenada: {codigos}"
	assert _ver(lista).json()["pins"][0]["voteCount"] == 3


@pytest.mark.critical
@pytest.mark.django_db
def test_no_se_puede_votar_un_item_de_otra_lista():
	"""La pertenencia es lo que vuelve inútil probar ids ajenos.

	El id del item viaja al cliente, así que es adivinable; lo que no se
	puede es usarlo bajo el token de otra lista.
	"""
	_, (ajeno,) = _lista_con_items()
	mia, _ = _lista_con_items()

	resp = _votar(mia, ajeno, uuid.uuid4())

	assert resp.status_code == 404, resp.content


@pytest.mark.django_db
def test_sacar_un_item_de_la_lista_se_lleva_sus_votos():
	"""No quedan filas colgadas de un item que ya no existe.

	Es el único observable que no tiene puerta pública: una vez borrado el
	item, sus votos no son alcanzables por ningún endpoint. Por eso este
	test —y sólo este— mira la base.
	"""
	lista, (item,) = _lista_con_items()
	_votar(lista, item, uuid.uuid4())
	assert ShortlistVote.objects.count() == 1

	item.delete()

	assert ShortlistVote.objects.count() == 0


@pytest.mark.django_db
def test_el_dueno_prende_y_apaga_la_votacion_de_su_lista():
	"""Sin esto el interruptor sólo existiría en el admin de Django."""
	lista, _ = _lista_con_items(voting_enabled=False)
	client = APIClient()
	client.force_authenticate(user=lista.user)

	resp = client.patch(
		reverse("shared-list-detail", args=[lista.id]),
		{"votingEnabled": True},
		format="json",
	)

	assert resp.status_code == 200, resp.content
	lista.refresh_from_db()
	assert lista.voting_enabled is True


@pytest.mark.critical
@pytest.mark.django_db
def test_nadie_prende_la_votacion_en_la_lista_de_otro():
	lista, _ = _lista_con_items(voting_enabled=False)
	client = APIClient()
	client.force_authenticate(user=UserFactory())

	resp = client.patch(
		reverse("shared-list-detail", args=[lista.id]),
		{"votingEnabled": True},
		format="json",
	)

	assert resp.status_code == 404, resp.content
	lista.refresh_from_db()
	assert lista.voting_enabled is False


@pytest.mark.django_db
def test_la_pagina_dice_cuanta_gente_voto():
	"""Sin el total, cuatro ticks en un item no dicen si falta alguien.

	Son personas distintas, no votos: quien marca tres lugares es una sola.
	"""
	lista, (uno, otro) = _lista_con_items(2)
	ana, cris = uuid.uuid4(), uuid.uuid4()
	_votar(lista, uno, ana)
	_votar(lista, otro, ana)
	_votar(lista, uno, cris)

	assert _ver(lista).json()["voterCount"] == 2


@pytest.mark.critical
@pytest.mark.django_db
def test_el_preflight_permite_la_cabecera_del_votante():
	"""Un header custom obliga al navegador a pedir permiso antes del POST.

	Si no está en `CORS_ALLOW_HEADERS`, el preflight se rechaza y el voto
	nunca sale — con un `Failed to fetch` que no distingue de estar sin red.
	Ningún test que llame a la vista directamente lo ve: el que corta es el
	navegador. Apareció mirando la pantalla, no leyendo el código.
	"""
	lista, (item,) = _lista_con_items()

	resp = APIClient().options(
		reverse("shortlist-votes", args=[lista.token]),
		HTTP_ORIGIN="http://localhost:5174",
		HTTP_ACCESS_CONTROL_REQUEST_METHOD="POST",
		HTTP_ACCESS_CONTROL_REQUEST_HEADERS="x-muse-voter",
	)

	permitidos = resp.headers.get("access-control-allow-headers", "")
	assert "x-muse-voter" in permitidos.lower(), permitidos
