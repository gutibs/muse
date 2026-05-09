import pytest


@pytest.fixture(autouse=True)
def _disable_throttles(settings):
	"""Throttle scopes (login, register, etc.) interfere with rapid-fire tests
	and would make the suite flaky depending on order. Strip them globally."""
	settings.REST_FRAMEWORK = {
		**settings.REST_FRAMEWORK,
		"DEFAULT_THROTTLE_CLASSES": (),
		"DEFAULT_THROTTLE_RATES": {},
	}
