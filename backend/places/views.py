"""Thin proxy to Google Places API (New).

Frontend never sees the API key — every request goes through here, and the
HTTP calls themselves live in places.services.google_places. What stays in
this module is the HTTP boundary: query parsing, the response shape the app
expects, throttling and auth.
"""

import logging

# Used by ReverseGeocodeView, which proxies Nominatim — a different provider
# from Google Places, whose client lives in places.services.google_places.
import requests
from django.conf import settings
from django.http import HttpResponseRedirect
from rest_framework import status
from rest_framework.decorators import (
	api_view,
	authentication_classes,
	permission_classes,
	throttle_classes,
)
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle, ScopedRateThrottle, UserRateThrottle
from rest_framework.views import APIView

from places.geo import parse_lat_lng
from places.services import google_places
from places.services import place_details as details_cache
from restaurants.services import google_place_parser

logger = logging.getLogger(__name__)

# Country/region words a user might type at the end of a city query to
# disambiguate (e.g. "London UK" → restrict to GB). Mapped to ISO-3166-1
# alpha-2 codes accepted by Google Places `includedRegionCodes`.
# Lowercased; matched against the trailing token(s) of the query.
_COUNTRY_HINTS = {
	# United Kingdom
	"uk": "gb",
	"u.k": "gb",
	"u.k.": "gb",
	"gb": "gb",
	"england": "gb",
	"scotland": "gb",
	"wales": "gb",
	"northern ireland": "gb",
	"great britain": "gb",
	"united kingdom": "gb",
	"britain": "gb",
	# United States
	"us": "us",
	"u.s": "us",
	"u.s.": "us",
	"usa": "us",
	"u.s.a": "us",
	"u.s.a.": "us",
	"united states": "us",
	"america": "us",
	# Canada
	"canada": "ca",
	"ca": "ca",
	# Australia / NZ
	"australia": "au",
	"au": "au",
	"new zealand": "nz",
	"nz": "nz",
	# Common European
	"ireland": "ie",
	"ie": "ie",
	"france": "fr",
	"fr": "fr",
	"spain": "es",
	"españa": "es",
	"es": "es",
	"italy": "it",
	"italia": "it",
	"it": "it",
	"germany": "de",
	"deutschland": "de",
	"de": "de",
	"portugal": "pt",
	"pt": "pt",
	"netherlands": "nl",
	"holland": "nl",
	"nl": "nl",
	"belgium": "be",
	"be": "be",
	"switzerland": "ch",
	"ch": "ch",
	"austria": "at",
	"at": "at",
	# LATAM
	"argentina": "ar",
	"ar": "ar",
	"brazil": "br",
	"brasil": "br",
	"br": "br",
	"chile": "cl",
	"cl": "cl",
	"mexico": "mx",
	"méxico": "mx",
	"mx": "mx",
	"uruguay": "uy",
	"uy": "uy",
	"colombia": "co",
	"co": "co",
	"peru": "pe",
	"perú": "pe",
	"pe": "pe",
	# APAC
	"japan": "jp",
	"jp": "jp",
	"china": "cn",
	"cn": "cn",
	"hong kong": "hk",
	"hk": "hk",
	"singapore": "sg",
	"sg": "sg",
	"india": "in",
	"in": "in",
}


def _extract_country_hint(query: str):
	"""Return (country_code, cleaned_query) if the trailing words of `query`
	match a known country name/code, else (None, query). Strips a trailing
	comma + the matched suffix so the query sent to Google is just the city.
	"""
	q = (query or "").strip()
	if not q:
		return None, q
	# Try multi-word suffixes first (e.g. "united kingdom"), then single word.
	lowered = q.lower().rstrip(",")
	for n in (3, 2, 1):
		parts = lowered.rsplit(" ", n)
		if len(parts) <= n:
			continue
		suffix = parts[-n] if n == 1 else " ".join(parts[-n:])
		suffix = suffix.strip(", ")
		code = _COUNTRY_HINTS.get(suffix)
		if code:
			head = q[: len(q) - len(suffix)].rstrip(", ").strip()
			return code, head or q
	return None, q


class PlacesThrottle(UserRateThrottle):
	scope = "places"


class PlacesAnonThrottle(AnonRateThrottle):
	scope = "places"


def _not_configured():
	return Response(
		{"detail": "Google Places API is not configured."},
		status=status.HTTP_503_SERVICE_UNAVAILABLE,
	)


def _location_bias(request, radius_m: float) -> dict | None:
	"""Optional map-centre bias. Bad client coordinates degrade to no bias
	rather than failing the search, but are logged."""
	lat = request.query_params.get("lat")
	lng = request.query_params.get("lng")
	if not lat or not lng:
		return None
	try:
		return {
			"circle": {
				"center": {"latitude": float(lat), "longitude": float(lng)},
				"radius": radius_m,
			}
		}
	except (TypeError, ValueError):
		logger.warning("ignoring non-numeric locationBias lat=%r lng=%r", lat, lng)
		return None


def _structured(prediction: dict) -> tuple[str, str]:
	fmt = prediction.get("structuredFormat", {})
	return (
		fmt.get("mainText", {}).get("text", ""),
		fmt.get("secondaryText", {}).get("text", ""),
	)


@api_view(["GET"])
@throttle_classes([PlacesThrottle])
def autocomplete(request):
	"""Autocomplete restaurant names as the user types."""
	if not google_places.is_configured():
		return _not_configured()

	query = request.query_params.get("q", "").strip()
	if not query or len(query) < 2:
		return Response({"results": []})

	body = {
		"input": query,
		"includedPrimaryTypes": ["restaurant", "cafe", "bar", "bakery", "meal_takeaway"],
	}
	bias = _location_bias(request, 50000.0)
	if bias:
		body["locationBias"] = bias

	try:
		predictions = google_places.autocomplete(body)
	except google_places.GooglePlacesError as exc:
		return Response({"detail": exc.message}, status=exc.status_code)

	results = []
	for p in predictions:
		main, secondary = _structured(p)
		results.append({"place_id": p.get("placeId"), "name": main, "address": secondary})
	return Response({"results": results})


@api_view(["GET"])
@throttle_classes([PlacesThrottle])
def city_autocomplete(request):
	"""Autocomplete city names."""
	if not google_places.is_configured():
		return _not_configured()

	query = request.query_params.get("q", "").strip()
	if not query or len(query) < 2:
		return Response({"results": []})

	# Detect "City, UK" / "City Canada" suffix and bias Google to that country.
	# Without this, "London UK" routinely returns London, Ontario first.
	country_code, city_query = _extract_country_hint(query)

	body = {
		"input": city_query or query,
		"includedPrimaryTypes": ["locality", "administrative_area_level_3"],
	}
	if country_code:
		body["includedRegionCodes"] = [country_code]
	else:
		# No explicit country hint: bias by the caller's current map view so
		# a bare "london" prefers the London the user is looking at over the
		# US-default Google falls back to.
		bias = _location_bias(request, 500000.0)
		if bias:
			body["locationBias"] = bias

	try:
		predictions = google_places.autocomplete(body)
	except google_places.GooglePlacesError as exc:
		return Response({"detail": exc.message}, status=exc.status_code)

	results = []
	for p in predictions:
		main, secondary = _structured(p)
		# "City, Country", or just the name when there is no secondary line.
		display = f"{main}, {secondary}" if secondary else main
		results.append({"place_id": p.get("placeId"), "name": main, "display": display})
	return Response({"results": results})


@api_view(["GET"])
@throttle_classes([PlacesThrottle])
def place_details(request, place_id: str):
	"""Fetch full details for a place. Returns normalized data ready to create a Restaurant."""
	if not google_places.is_configured():
		return _not_configured()

	try:
		payload = details_cache.get_details(place_id, google_place_parser.FIELD_MASK)
	except google_places.GooglePlacesError as exc:
		return Response({"detail": exc.message}, status=exc.status_code)

	# Parsing and truncation live in the parser, shared with the importer, so
	# this endpoint and `from_google` can never disagree about the same place.
	parsed = google_place_parser.parse_place(payload)
	return Response({k: v for k, v in parsed.items() if k != "photo_ref"})


class ReverseGeocodeView(APIView):
	"""Server-side proxy to Nominatim reverse geocoding.

	Direct browser hits to nominatim.openstreetmap.org violated their usage
	policy (no User-Agent, no rate limiting, can't be identified). This
	endpoint:
	  - Sends a User-Agent identifying the app + a contact email.
	  - Throttles per-user to 60/hour (Nominatim policy is 1 req/sec; we
	    stay well below that even with N concurrent users).
	  - Requires authentication so anonymous abuse can't burn our quota.
	"""

	permission_classes = [IsAuthenticated]
	throttle_classes = [ScopedRateThrottle]
	throttle_scope = "reverse_geocode"

	def get(self, request):
		# Same parsing as RestaurantViewSet.nearby — see places.geo.
		lat, lng = parse_lat_lng(request.query_params)

		try:
			r = requests.get(
				"https://nominatim.openstreetmap.org/reverse",
				params={
					"format": "json",
					"lat": lat,
					"lon": lng,
					"zoom": 18,
					"addressdetails": 1,
					"email": settings.APP_CONTACT_EMAIL,
				},
				headers={
					"User-Agent": settings.NOMINATIM_USER_AGENT,
					"Accept-Language": "en",
				},
				timeout=10,
			)
			r.raise_for_status()
			data = r.json()
		except requests.RequestException:
			logger.exception("nominatim reverse-geocode failed for lat=%s lng=%s", lat, lng)
			return Response(
				{"detail": "reverse geocode failed"},
				status=status.HTTP_502_BAD_GATEWAY,
			)

		# Forward only what the frontend needs. The full nested address
		# dict is preserved so LocationPicker.svelte can keep its current
		# parser (road / house_number / city|town|village|municipality / country).
		return Response(
			{
				"display_name": data.get("display_name"),
				"address": data.get("address", {}),
			}
		)


@api_view(["GET"])
@authentication_classes([])
@permission_classes([AllowAny])
@throttle_classes([PlacesAnonThrottle, PlacesThrottle])
def place_photo(request):
	"""Redirect to the signed Google URL for a place photo.

	Public: <img src> tags can't send Authorization headers. Only returns a
	302 to a Google-hosted CDN URL, so there's no private data to leak.
	Throttled to stop abuse of our Google quota.

	Query: ref (photo resource name)
	"""
	if not google_places.is_configured():
		return _not_configured()

	try:
		# The service validates the ref shape and that the resolved URL points
		# at Google-owned storage before we hand the user a redirect.
		uri = google_places.photo_uri(request.query_params.get("ref", ""))
	except google_places.GooglePlacesError as exc:
		return Response({"detail": exc.message}, status=exc.status_code)

	return HttpResponseRedirect(uri)
