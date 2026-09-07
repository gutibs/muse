import pytest
from django.core.cache import cache


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
def _disable_throttles(settings):
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
	"""
	settings.REST_FRAMEWORK = {
		**settings.REST_FRAMEWORK,
		"DEFAULT_THROTTLE_CLASSES": (),
		"DEFAULT_THROTTLE_RATES": {
			scope: "10000/hour" for scope in settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]
		},
	}
