from unittest.mock import Mock

import pytest
import resend
from django.conf import settings as django_settings
from django.core.cache import cache
from rest_framework.throttling import SimpleRateThrottle

# Las rates que corren en producción, capturadas antes de que nadie las pise.
# Importar `rest_framework.throttling` acá además vuelve determinista el momento
# del import, que es de lo que dependía todo esto.
RATES_REALES = dict(django_settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"])


@pytest.fixture(autouse=True)
def _sin_emails_reales(monkeypatch):
	"""Ningún test toca la API de Resend.

	Antes la tocaban todos: cada alta llamaba a Resend por la red, y no llegaba
	un mail sólo porque la API rechaza `@example.com`. Con un dominio válido en
	un test, la suite le escribe a una persona de verdad — y de paso pasar los
	tests dependía de tener red y cupo.

	Se parchea `resend.Emails.send`, que es el único punto por donde
	`accounts.services.email` sale. Los tests que quieren mirar el payload piden
	el fixture `emails_enviados`; los que ya traen su propio `@patch` sobre el
	mismo atributo siguen funcionando, porque se aplica encima de éste.

	`tests/test_no_emails_reales.py` lo vigila.
	"""
	enviados = Mock(return_value={"id": "re_test_fake"})
	monkeypatch.setattr(resend.Emails, "send", enviados)
	return enviados


@pytest.fixture
def emails_enviados(_sin_emails_reales):
	"""El mock de Resend, para inspeccionar qué se mandó y a quién."""
	return _sin_emails_reales


@pytest.fixture(autouse=True)
def _reset_throttle_cache():
	"""DRF stores per-view throttle history in the cache, keyed by scope +
	client ident. That cache is process-global and survives between tests, so
	repeated POSTs to the same throttled endpoint (e.g. /auth/register/) across
	tests accumulate and eventually trip the limit — a 429 in a test that has
	nothing to do with rate limiting. Clear it around every test for isolation.
	"""
	cache.clear()
	yield
	cache.clear()


@pytest.fixture(autouse=True)
def _disable_throttles(settings, monkeypatch):
	"""Saca los throttles globales para que los tests puedan disparar rápido.

	Los throttles por vista (`ScopedRateThrottle` en places, app-version, etc.)
	resuelven su `scope` contra `DEFAULT_THROTTLE_RATES` **al instanciarse**, así
	que vaciar el dict les da `ImproperlyConfigured`. Por eso se mapean todos a
	un rate altísimo en vez de borrarlos.

	**Los scopes salen de los settings reales, no de una lista a mano.** Antes
	estaban enumerados acá: cada scope nuevo rompía la suite con un `KeyError`
	que no tenía nada que ver con el cambio que lo destapaba, y la lista crecía
	por omisión — el mismo tipo de bug que la revisión de F2.E encontró en los
	campos del perfil ajeno.

	**Se parchea también `SimpleRateThrottle.THROTTLE_RATES`, y esa es la parte
	que hace el trabajo.** DRF evalúa
	`THROTTLE_RATES = api_settings.DEFAULT_THROTTLE_RATES` en el cuerpo de la
	clase: una referencia al dict que existía al importar el módulo. Reemplazar
	`settings.REST_FRAMEWORK` crea un dict nuevo que esa referencia nunca ve, así
	que durante mucho tiempo esta fixture no desactivó nada y los throttles
	corrieron con las rates de producción. Que la suite pasara igual dependía de
	**cuándo** se importaba `rest_framework.throttling`: dentro de un test
	capturaba las rates altas, en la colección las reales. El mismo test pasaba
	solo y fallaba acompañado. `tests/test_throttle_isolation.py` lo vigila.
	"""
	altas = dict.fromkeys(RATES_REALES, "10000/hour")
	settings.REST_FRAMEWORK = {
		**settings.REST_FRAMEWORK,
		"DEFAULT_THROTTLE_CLASSES": (),
		"DEFAULT_THROTTLE_RATES": altas,
	}
	monkeypatch.setattr(SimpleRateThrottle, "THROTTLE_RATES", altas)


@pytest.fixture
def rates_de_produccion(settings, monkeypatch):
	"""Repone las rates reales para un test que mide el rate limit.

	Devuelve una función que acepta overrides por scope, para bajar un límite
	y no tener que mandar 300 requests:

		def test_x(rates_de_produccion):
			rates_de_produccion(shortlist_vote="3/hour")

	Sale de `RATES_REALES` en vez de una copia a mano: una copia enumerada en el
	test se desactualiza en silencio y termina midiendo un límite que ya no
	existe. `NUM_PROXIES` se repone porque sin él DRF identifica al cliente por
	la cadena `X-Forwarded-For` completa —que el cliente controla— y el test
	mediría otra cosa.
	"""

	def _fijar(**overrides):
		rates = {**RATES_REALES, **overrides}
		settings.REST_FRAMEWORK = {
			**settings.REST_FRAMEWORK,
			"DEFAULT_THROTTLE_RATES": rates,
			"NUM_PROXIES": 1,
		}
		monkeypatch.setattr(SimpleRateThrottle, "THROTTLE_RATES", rates)
		cache.clear()
		return rates

	return _fijar
