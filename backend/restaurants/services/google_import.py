"""Import a Restaurant from a Google Place ID.

Extracted from RestaurantViewSet.from_google (137 lines of mixed view +
HTTP client + parsing + race-safe persistence) into a single service
function. Race-safety, defensive truncation, and the auto-approve
decision (D-002) live here.

The HTTP call to Google Places stays inline in this module rather than
being shared with `places/views.py` — that's a separate refactor (would
extract a `places/client.py`). See B-006 discussion.
"""

from __future__ import annotations

import logging
from collections.abc import Callable

import requests
from django.conf import settings
from django.contrib.gis.geos import Point
from django.db import IntegrityError

from restaurants.models import Restaurant

logger = logging.getLogger(__name__)


PLACES_API_BASE = "https://places.googleapis.com/v1"
_FIELD_MASK = ",".join(
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
	]
)


class GoogleImportError(Exception):
	"""Raised when import from Google fails for any reason the caller
	should surface as an HTTP error. `status_code` is the HTTP status the
	view should return."""

	def __init__(self, message: str, status_code: int = 502):
		super().__init__(message)
		self.message = message
		self.status_code = status_code


def normalize_place_id(place_id: str) -> str:
	"""Places API (New) sometimes returns IDs as 'places/ChIJ...'; the bare
	ID is what we store, so normalise on input/output."""
	if place_id.startswith("places/"):
		return place_id.split("/", 1)[1]
	return place_id


def fetch_place_details(place_id: str) -> dict:
	"""Hit Google Places API for the field set we care about. Raises
	GoogleImportError on any network/HTTP failure."""
	key = settings.GOOGLE_PLACES_API_KEY
	if not key:
		raise GoogleImportError("Google Places API is not configured.", status_code=503)

	try:
		r = requests.get(
			f"{PLACES_API_BASE}/places/{place_id}",
			headers={
				"X-Goog-Api-Key": key,
				"X-Goog-FieldMask": _FIELD_MASK,
			},
			timeout=5,
		)
		r.raise_for_status()
		return r.json()
	except requests.RequestException as exc:
		logger.exception("from_google: Google Places fetch failed for %s", place_id)
		raise GoogleImportError("Could not verify place with Google.", status_code=502) from exc


def normalize_place_data(
	payload: dict,
	*,
	photo_url_builder: Callable[[str], str] | None = None,
) -> dict:
	"""Map a Google Places response to Restaurant kwargs.

	Defensive truncation against Google occasionally returning strings
	longer than our column limits. `photo_url_builder` lets the caller
	produce an absolute URL to our own photo proxy without coupling this
	module to `request.build_absolute_uri`.
	"""
	location = payload.get("location") or {}
	lat = location.get("latitude")
	lng = location.get("longitude")
	if lat is None or lng is None:
		raise GoogleImportError("Place has no location.", status_code=400)

	city = ""
	country = ""
	for comp in payload.get("addressComponents", []):
		types = comp.get("types", [])
		if "locality" in types and not city:
			city = comp.get("longText", "")
		elif "administrative_area_level_1" in types and not city:
			city = comp.get("longText", "")
		elif "country" in types:
			country = comp.get("longText", "")

	photo_url = ""
	photos = payload.get("photos") or []
	if photos and photo_url_builder is not None:
		photo_name = photos[0].get("name")
		if photo_name:
			photo_url = photo_url_builder(photo_name)

	hours = payload.get("regularOpeningHours") or {}
	name = ((payload.get("displayName") or {}).get("text", "") or "Unknown")[:200]

	return {
		"name": name,
		"location": Point(float(lng), float(lat), srid=4326),
		"address": (payload.get("formattedAddress", "") or "")[:300],
		"city": city[:100],
		"country": country[:100],
		"website": (payload.get("websiteUri", "") or "")[:500],
		"phone": (payload.get("internationalPhoneNumber", "") or "")[:30],
		"image_url": photo_url[:2000],
		"opening_hours": hours.get("weekdayDescriptions", []) or [],
	}


def import_from_google_place_id(
	place_id: str,
	user,
	*,
	photo_url_builder: Callable[[str], str] | None = None,
) -> tuple[Restaurant, bool]:
	"""Find or create a Restaurant from a Google placeId.

	Returns ``(restaurant, created)``. Race-safe: two concurrent calls
	with the same place_id produce a single Restaurant — the loser of the
	race detects the IntegrityError and re-fetches the row.

	Raises ``GoogleImportError`` with an HTTP-mappable status_code on
	failure (missing API key → 503, fetch failure → 502, place has no
	location → 400, validation mismatch → 400, persistence failure → 500).

	The auto-approve decision (always APPROVED for Google-sourced rows)
	is documented in docs/PRODUCT_DECISIONS.md D-002.
	"""
	place_id = normalize_place_id(place_id)

	existing = Restaurant.objects.filter(google_place_id=place_id).first()
	if existing:
		return existing, False

	payload = fetch_place_details(place_id)

	# Verify the response echoes back the place_id we asked for. Google
	# may format it as "places/ChIJ..." or bare; accept both.
	returned_id = normalize_place_id(payload.get("id") or "")
	if returned_id and returned_id != place_id:
		raise GoogleImportError("Invalid placeId.", status_code=400)

	fields = normalize_place_data(payload, photo_url_builder=photo_url_builder)

	try:
		restaurant = Restaurant.objects.create(
			google_place_id=place_id,
			created_by=user,
			approval_status=Restaurant.ApprovalStatus.APPROVED,
			**fields,
		)
		return restaurant, True
	except IntegrityError:
		# Race: another request created the same place_id between our
		# SELECT above and the INSERT here. Fetch and return the existing
		# row. If it's somehow STILL not there, surface as 500 — we know
		# the unique constraint fired but can't find what triggered it.
		existing = Restaurant.objects.filter(google_place_id=place_id).first()
		if existing:
			return existing, False
		logger.exception(
			"from_google integrity error for place_id=%s but no existing row found; payload=%r",
			place_id,
			payload,
		)
		raise GoogleImportError("Could not save this place.", status_code=500) from None
	except Exception as exc:
		logger.exception(
			"from_google failed to create restaurant for place_id=%s payload=%r",
			place_id,
			payload,
		)
		raise GoogleImportError("Could not save this place.", status_code=500) from exc
