import pytest


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
		},
	}
