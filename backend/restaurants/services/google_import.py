"""Import a Restaurant from a Google Place ID.

Extracted from RestaurantViewSet.from_google (137 lines of mixed view +
HTTP client + parsing + race-safe persistence) into a single service
function. Race-safety, defensive truncation, and the auto-approve
decision (D-002) live here.

The HTTP call itself lives in `places.services.google_places`, shared with
`places/views.py` — this module keeps the parsing, the defensive truncation
and the race-safe persistence.
"""

from __future__ import annotations

import logging

from django.contrib.gis.geos import Point
from django.db import IntegrityError

from places.services import google_places
from places.services.place_details import get_details
from restaurants.models import Restaurant, Tag
from restaurants.services.google_place_parser import (
	FIELD_MASK,
	inferred_tag_slugs,
	parse_place,
)

logger = logging.getLogger(__name__)


class GoogleImportError(Exception):
	"""Raised when import from Google fails for any reason the caller
	should surface as an HTTP error. `status_code` is the HTTP status the
	view should return."""

	def __init__(self, message: str, status_code: int = 502):
		super().__init__(message)
		self.message = message
		self.status_code = status_code


# Re-exported: the canonical implementation is in the Places client, but
# this module's callers have always imported it from here.
normalize_place_id = google_places.normalize_place_id


def fetch_place_details(place_id: str) -> dict:
	"""Hit Google Places API for the field set we care about.

	Delegates to places.services.place_details, which serves the 30-day cache
	when it can and falls through to the single HTTP client when it cannot,
	and re-raises its failures as GoogleImportError so this module keeps one
	exception type for its callers.
	"""
	try:
		return get_details(place_id, FIELD_MASK)
	except google_places.GooglePlacesError as exc:
		raise GoogleImportError(exc.message, status_code=exc.status_code) from exc


def restaurant_kwargs(payload: dict) -> dict:
	"""Map a Google Places response to Restaurant constructor kwargs.

	Normalization and truncation live in `google_place_parser`; what stays
	here is the part only a persisting caller can decide — that a place
	without coordinates is a 400 rather than a row with a null location.
	"""
	parsed = parse_place(payload)
	lat, lng = parsed["lat"], parsed["lng"]
	if lat is None or lng is None:
		raise GoogleImportError("Place has no location.", status_code=400)

	return {
		"name": parsed["name"] or "Unknown",
		"location": Point(float(lng), float(lat), srid=4326),
		"address": parsed["address"],
		"city": parsed["city"],
		"district": parsed["district"],
		"country": parsed["country"],
		"website": parsed["website"],
		"phone": parsed["phone"],
		"image_url": parsed["image_url"],
		"opening_hours": parsed["opening_hours"],
	}


def _mark_attributes(restaurant: Restaurant, payload: dict) -> None:
	"""Marca en el restaurante lo que Google afirma del local.

	Terraza, música en vivo y perros son hechos del lugar, no opiniones de
	quien lo guarda: por eso van en `Restaurant.tags` y no en el pin. La
	pantalla de pin los lee de ahí para venir con esos chips ya marcados.

	Sólo se agrega: nunca se quita una etiqueta que alguien puso a mano.
	"""
	slugs = inferred_tag_slugs(payload)
	if not slugs:
		return
	tags = list(Tag.objects.filter(slug__in=slugs))
	if tags:
		restaurant.tags.add(*tags)


def import_from_google_place_id(place_id: str, user) -> tuple[Restaurant, bool]:
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

	fields = restaurant_kwargs(payload)

	try:
		restaurant = Restaurant.objects.create(
			google_place_id=place_id,
			created_by=user,
			approval_status=Restaurant.ApprovalStatus.APPROVED,
			**fields,
		)
		_mark_attributes(restaurant, payload)
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
