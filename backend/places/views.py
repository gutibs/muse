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

logger = logging.getLogger(__name__)

PLACES_API_BASE = "https://places.googleapis.com/v1"

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

	body = {
		"input": query,
		"includedPrimaryTypes": ["locality", "administrative_area_level_3"],
	}

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
		try:
			lat = float(request.query_params.get("lat", ""))
			lng = float(request.query_params.get("lng", ""))
		except ValueError:
			return Response(
				{"detail": "lat and lng must be numeric"},
				status=status.HTTP_400_BAD_REQUEST,
			)
		if not (-90 <= lat <= 90 and -180 <= lng <= 180):
			return Response(
				{"detail": "lat/lng out of range"},
				status=status.HTTP_400_BAD_REQUEST,
			)

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
