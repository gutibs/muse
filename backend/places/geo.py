"""Parsing of geographic query params, shared by every view that takes
coordinates from the client.

Lived inline in ReverseGeocodeView (correctly) and in
RestaurantViewSet.nearby (incorrectly — bare `float()` calls that turned a
malformed request into a 500). One implementation so the next endpoint that
takes a lat/lng inherits the guards instead of re-deriving them.

Raises DRF's ValidationError, which the framework renders as a 400.
"""

from rest_framework.exceptions import ValidationError

# A restaurant discovery radius beyond this is never a real user intent; it
# is a malformed client or someone probing. Clamped rather than rejected so
# a sloppy caller still gets a useful answer.
MAX_RADIUS_KM = 50.0
DEFAULT_RADIUS_KM = 5.0

# Degrees of latitude per kilometre. Used to express a kilometre radius as
# the degree distance `__dwithin` expects on a geographic (4326) field.
KM_PER_DEGREE = 111.32


def parse_lat_lng(params) -> tuple[float, float]:
	"""Return (lat, lng) from a query dict, or raise ValidationError (400)."""
	lat_raw = params.get("lat")
	lng_raw = params.get("lng")

	if not lat_raw or not lng_raw:
		raise ValidationError({"detail": "lat and lng are required."})

	try:
		lat = float(lat_raw)
		lng = float(lng_raw)
	except (TypeError, ValueError):
		raise ValidationError({"detail": "lat and lng must be numeric."}) from None

	if not (-90 <= lat <= 90 and -180 <= lng <= 180):
		raise ValidationError({"detail": "lat/lng out of range."})

	return lat, lng


def parse_radius_km(params, *, default: float = DEFAULT_RADIUS_KM) -> float:
	"""Return a radius in km, clamped to MAX_RADIUS_KM.

	Absent → default. Non-numeric or non-positive → ValidationError (400),
	because those signal a broken client rather than an ambitious search.
	"""
	raw = params.get("radius")
	if raw in (None, ""):
		return default

	try:
		radius = float(raw)
	except (TypeError, ValueError):
		raise ValidationError({"detail": "radius must be numeric."}) from None

	if radius <= 0:
		raise ValidationError({"detail": "radius must be greater than 0."})

	return min(radius, MAX_RADIUS_KM)
