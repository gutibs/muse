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
	"""Strip the global throttle classes so rapid-fire tests don't trip
	rate limits. Per-view throttle classes (e.g. RegisterAnonThrottle,
	ScopedRateThrottle on places) still try to resolve their `scope`
	against `DEFAULT_THROTTLE_RATES` at instantiation time, so we keep
	every known scope mapped to a very-high rate instead of clearing
	the dict — clearing would raise ImproperlyConfigured when those
	per-view throttles instantiate.
	"""
	settings.REST_FRAMEWORK = {
		**settings.REST_FRAMEWORK,
		"DEFAULT_THROTTLE_CLASSES": (),
		"DEFAULT_THROTTLE_RATES": {
			"anon": "10000/hour",
			"user": "10000/hour",
			"login": "10000/min",
			"register": "10000/hour",
			"user_search": "10000/hour",
			"places": "10000/hour",
			"invite": "10000/hour",
			"reverse_geocode": "10000/hour",
			"shared_list_public": "10000/hour",
			"analytics": "10000/hour",
		},
	}
