"""RF14 — el rate limit cuenta por cliente real, no por lo que el cliente diga.

La spec describe el síntoma al revés: sin NUM_PROXIES, DRF NO cae a
REMOTE_ADDR mientras haya X-Forwarded-For — usa la cadena XFF entera como
identidad (`get_ident` en rest_framework/throttling.py). Como nginx appendea
con $proxy_add_x_forwarded_for, esa cadena arranca con lo que mandó el
cliente, así que un XFF distinto en cada request da un cubo nuevo en cada
request y el throttle no existe. Con NUM_PROXIES=1 DRF toma la última
posición —la que puso nginx— y el prefijo falsificado deja de importar.

Afecta a login, register y shared_list_public tanto como al reset.
"""

import pytest
from django.urls import reverse
from rest_framework.settings import api_settings
from rest_framework.test import APIClient


@pytest.fixture(autouse=True)
def _rates_reales(rates_de_produccion):
	"""Estos tests miden el rate limit, así que necesitan el límite real.

	Antes esto era un fixture local que reemplazaba `settings.REST_FRAMEWORK`
	con una copia a mano de los scopes. **No hacía nada**: DRF lee
	`SimpleRateThrottle.THROTTLE_RATES`, una referencia al dict del import, y
	los tests pasaban de casualidad porque ese dict tenía justo las rates que
	la copia declaraba. Al arreglar el conftest —que ahora sí desactiva los
	throttles— los cuatro se cayeron de golpe, que es como se supo.
	"""
	rates_de_produccion()


def _through_nginx(client_sent, real_ip):
	"""Lo que ve Django después de que nginx appendea la IP del socket."""
	return f"{client_sent}, {real_ip}" if client_sent else real_ip


@pytest.mark.critical
@pytest.mark.django_db
def test_a_forged_forwarded_for_does_not_buy_a_fresh_bucket():
	"""El atacante controla el prefijo del XFF; no debe comprarle un cubo."""
	url = reverse("password_reset")
	client = APIClient()
	attacker_ip = "203.0.113.9"

	for i in range(5):
		client.post(
			url,
			{"email": "victim@example.com"},
			format="json",
			HTTP_X_FORWARDED_FOR=_through_nginx(f"10.0.0.{i}", attacker_ip),
		)

	# Sexto pedido, con otro XFF inventado: sigue siendo el mismo cliente.
	evasion = client.post(
		url,
		{"email": "victim@example.com"},
		format="json",
		HTTP_X_FORWARDED_FOR=_through_nginx("10.0.0.99", attacker_ip),
	)
	assert evasion.status_code == 429, evasion.content


@pytest.mark.critical
@pytest.mark.django_db
def test_two_clients_behind_the_proxy_get_separate_buckets():
	url = reverse("password_reset")
	client = APIClient()

	# El primero agota su cuota de 5/hora.
	for _ in range(5):
		client.post(
			url, {"email": "a@example.com"}, format="json", HTTP_X_FORWARDED_FOR="203.0.113.1"
		)
	blocked = client.post(
		url, {"email": "a@example.com"}, format="json", HTTP_X_FORWARDED_FOR="203.0.113.1"
	)
	assert blocked.status_code == 429, blocked.content

	# El segundo, detrás del mismo nginx, todavía tiene la suya entera.
	other = client.post(
		url, {"email": "b@example.com"}, format="json", HTTP_X_FORWARDED_FOR="198.51.100.7"
	)
	assert other.status_code == 200, other.content


@pytest.mark.critical
@pytest.mark.django_db
def test_num_proxies_is_configured():
	"""Se chequea sobre api_settings, no sobre django.conf.settings: DRF lee
	NUM_PROXIES del dict REST_FRAMEWORK, y un setting suelto a nivel de módulo
	deja api_settings.NUM_PROXIES en None sin que nada avise."""
	assert api_settings.NUM_PROXIES == 1


@pytest.mark.critical
@pytest.mark.django_db
def test_an_authenticated_caller_is_throttled_too():
	"""`AnonRateThrottle.get_cache_key` devuelve None si hay sesión, o sea que
	no cuenta nada. Como el registro es abierto, una cuenta gratis alcanzaba
	para rociar mails de reset a direcciones de terceros desde nuestro dominio
	de Resend, sin tope: el cooldown por destino son 3 por casilla, no un tope
	global de envíos."""
	from tests.factories import UserFactory

	user = UserFactory(username="spammer", email="spammer@example.com")
	tokens = (
		APIClient()
		.post(
			reverse("token_obtain"),
			{"username": user.username, "password": "test-pass-123"},
			format="json",
		)
		.json()
	)
	client = APIClient(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
	url = reverse("password_reset")

	statuses = [
		client.post(url, {"email": f"victim{i}@example.com"}, format="json").status_code
		for i in range(7)
	]

	assert 429 in statuses, f"ninguna request fue frenada: {statuses}"


@pytest.mark.critical
@pytest.mark.django_db
def test_an_authenticated_caller_is_throttled_on_confirm_too():
	from tests.factories import UserFactory

	user = UserFactory(username="guesser", email="guesser@example.com")
	tokens = (
		APIClient()
		.post(
			reverse("token_obtain"),
			{"username": user.username, "password": "test-pass-123"},
			format="json",
		)
		.json()
	)
	client = APIClient(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
	url = reverse("password_reset_confirm")

	statuses = [
		client.post(
			url,
			{"email": "victim@example.com", "code": "000000", "newPassword": "Nu3va-clave!"},
			format="json",
		).status_code
		for i in range(12)
	]

	assert 429 in statuses, f"ninguna request fue frenada: {statuses}"
