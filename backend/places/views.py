"""Thin proxy to Google Places API (New).

Frontend never sees the API key — all requests go through here.
We only forward the fields we actually need.
"""

import logging
from urllib.parse import urlparse

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

logger = logging.getLogger(__name__)

PLACES_API_BASE = "https://places.googleapis.com/v1"

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


_ALLOWED_PHOTO_HOSTS = {
	"places.googleapis.com",
	"lh3.googleusercontent.com",
	"lh4.googleusercontent.com",
	"lh5.googleusercontent.com",
	"lh6.googleusercontent.com",
	"maps.googleapis.com",
	"maps.gstatic.com",
}


class PlacesThrottle(UserRateThrottle):
	scope = "places"


class PlacesAnonThrottle(AnonRateThrottle):
	scope = "places"


def _not_configured():
	return Response(
		{"detail": "Google Places API is not configured."},
		status=status.HTTP_503_SERVICE_UNAVAILABLE,
	)


@api_view(["GET"])
@throttle_classes([PlacesThrottle])
def autocomplete(request):
	"""Autocomplete restaurant names as the user types."""
	key = settings.GOOGLE_PLACES_API_KEY
	if not key:
		return _not_configured()

	query = request.query_params.get("q", "").strip()
	if not query or len(query) < 2:
		return Response({"results": []})

	body = {
		"input": query,
		"includedPrimaryTypes": ["restaurant", "cafe", "bar", "bakery", "meal_takeaway"],
	}

	lat = request.query_params.get("lat")
	lng = request.query_params.get("lng")
	if lat and lng:
		try:
			body["locationBias"] = {
				"circle": {
					"center": {"latitude": float(lat), "longitude": float(lng)},
					"radius": 50000.0,
				}
			}
		except ValueError:
			# Bad client-provided lat/lng — fall back to no bias instead of
			# 500ing. Worth logging so DevTools / metrics can see it.
			logger.warning(
				"autocomplete: ignoring non-numeric locationBias lat=%r lng=%r", lat, lng
			)

	try:
		r = requests.post(
			f"{PLACES_API_BASE}/places:autocomplete",
			json=body,
			headers={
				"Content-Type": "application/json",
				"X-Goog-Api-Key": key,
			},
			timeout=5,
		)
		r.raise_for_status()
		data = r.json()
	except requests.RequestException as exc:
		logger.exception("Google Places API call failed: %s", exc)
		return Response({"detail": "Places API error."}, status=502)

	results = []
	for s in data.get("suggestions", []):
		p = s.get("placePrediction")
		if not p:
			continue
		results.append(
			{
				"place_id": p.get("placeId"),
				"name": p.get("structuredFormat", {}).get("mainText", {}).get("text", ""),
				"address": p.get("structuredFormat", {}).get("secondaryText", {}).get("text", ""),
			}
		)
	return Response({"results": results})


@api_view(["GET"])
@throttle_classes([PlacesThrottle])
def city_autocomplete(request):
	"""Autocomplete city names."""
	key = settings.GOOGLE_PLACES_API_KEY
	if not key:
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
		lat = request.query_params.get("lat")
		lng = request.query_params.get("lng")
		if lat and lng:
			try:
				body["locationBias"] = {
					"circle": {
						"center": {"latitude": float(lat), "longitude": float(lng)},
						"radius": 500000.0,
					}
				}
			except (TypeError, ValueError):
				logger.warning(
					"city_autocomplete: ignoring non-numeric locationBias lat=%r lng=%r",
					lat,
					lng,
				)

	try:
		r = requests.post(
			f"{PLACES_API_BASE}/places:autocomplete",
			json=body,
			headers={
				"Content-Type": "application/json",
				"X-Goog-Api-Key": key,
			},
			timeout=5,
		)
		r.raise_for_status()
		data = r.json()
	except requests.RequestException as exc:
		logger.exception("Google Places API call failed: %s", exc)
		return Response({"detail": "Places API error."}, status=502)

	results = []
	for s in data.get("suggestions", []):
		p = s.get("placePrediction")
		if not p:
			continue
		main = p.get("structuredFormat", {}).get("mainText", {}).get("text", "")
		secondary = p.get("structuredFormat", {}).get("secondaryText", {}).get("text", "")
		# Build "City, Country" or just name if no secondary
		display = f"{main}, {secondary}" if secondary else main
		results.append(
			{
				"place_id": p.get("placeId"),
				"name": main,
				"display": display,
			}
		)
	return Response({"results": results})


@api_view(["GET"])
@throttle_classes([PlacesThrottle])
def place_details(request, place_id: str):
	"""Fetch full details for a place. Returns normalized data ready to create a Restaurant."""
	key = settings.GOOGLE_PLACES_API_KEY
	if not key:
		return _not_configured()

	fields = ",".join(
		[
			"id",
			"displayName",
			"formattedAddress",
			"addressComponents",
			"location",
			"websiteUri",
			"internationalPhoneNumber",
			"regularOpeningHours",
			"photos",
			"primaryTypeDisplayName",
		]
	)

	try:
		r = requests.get(
			f"{PLACES_API_BASE}/places/{place_id}",
			headers={
				"X-Goog-Api-Key": key,
				"X-Goog-FieldMask": fields,
			},
			timeout=5,
		)
		r.raise_for_status()
		p = r.json()
	except requests.RequestException as exc:
		logger.exception("Google Places API call failed: %s", exc)
		return Response({"detail": "Places API error."}, status=502)

	city = ""
	country = ""
	for comp in p.get("addressComponents", []):
		types = comp.get("types", [])
		if "locality" in types:
			city = comp.get("longText", "")
		elif "administrative_area_level_1" in types and not city:
			city = comp.get("longText", "")
		elif "country" in types:
			country = comp.get("longText", "")

	photo_url = ""
	photos = p.get("photos") or []
	if photos:
		photo_name = photos[0].get("name")
		if photo_name:
			# Absolute URL so it passes URLField validation when persisted.
			photo_url = request.build_absolute_uri(f"/api/v1/places/photo/?ref={photo_name}")

	location = p.get("location") or {}
	hours = p.get("regularOpeningHours") or {}

	return Response(
		{
			"place_id": p.get("id"),
			"name": (p.get("displayName") or {}).get("text", ""),
			"address": p.get("formattedAddress", ""),
			"city": city,
			"country": country,
			"lat": location.get("latitude"),
			"lng": location.get("longitude"),
			"website": p.get("websiteUri", ""),
			"phone": p.get("internationalPhoneNumber", ""),
			"image_url": photo_url,
			"opening_hours": hours.get("weekdayDescriptions", []),
			"type": (p.get("primaryTypeDisplayName") or {}).get("text", ""),
		}
	)


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
	key = settings.GOOGLE_PLACES_API_KEY
	if not key:
		return _not_configured()

	photo_ref = request.query_params.get("ref", "").strip()
	if not photo_ref or not photo_ref.startswith("places/"):
		return Response({"detail": "Invalid ref."}, status=400)

	try:
		r = requests.get(
			f"{PLACES_API_BASE}/{photo_ref}/media",
			params={"maxWidthPx": 800, "skipHttpRedirect": "true"},
			headers={"X-Goog-Api-Key": key},
			timeout=5,
		)
		r.raise_for_status()
		data = r.json()
	except requests.RequestException as exc:
		logger.exception("Google Places API call failed: %s", exc)
		return Response({"detail": "Places API error."}, status=502)

	photo_uri = (data.get("photoUri") or "").strip()
	if not photo_uri.startswith("https://"):
		return Response({"detail": "Invalid photo URL."}, status=502)

	parsed = urlparse(photo_uri)
	host = (parsed.hostname or "").lower()
	if host not in _ALLOWED_PHOTO_HOSTS and not host.endswith(".googleusercontent.com"):
		return Response({"detail": "Untrusted photo host."}, status=502)

	return HttpResponseRedirect(photo_uri)
