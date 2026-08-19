"""HTTP client for the Google Places API (New).

The one place that talks to Google. Before this, the same request/raise/parse
block existed three times: twice in places/views.py (`autocomplete` and
`city_autocomplete`, near-identical) and once in
restaurants/services/google_import.py — whose own docstring flagged the
duplication and deferred the extraction. This is that extraction.

Callers get parsed data or a GooglePlacesError carrying the HTTP status the
view should surface; nobody outside this module handles `requests` exceptions
or knows the API key exists.
"""

from __future__ import annotations

import logging
import re
from urllib.parse import urlparse

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

PLACES_API_BASE = "https://places.googleapis.com/v1"
TIMEOUT_SECONDS = 5

# Google place ids are opaque URL-safe tokens. Validated before being
# interpolated into a request path so a crafted id cannot walk out of
# /places/ into another Google endpoint on our API key.
_PLACE_ID_RE = re.compile(r"^[A-Za-z0-9_-]+$")

# A photo redirect must land on Google-owned storage. Anything else means the
# upstream payload was not what we think it is.
_ALLOWED_PHOTO_HOSTS = {
	"places.googleapis.com",
	"lh3.googleusercontent.com",
	"lh4.googleusercontent.com",
	"lh5.googleusercontent.com",
	"lh6.googleusercontent.com",
	"maps.googleapis.com",
	"maps.gstatic.com",
}


class GooglePlacesError(Exception):
	"""Failure the caller should surface as an HTTP error.

	`status_code` is what the view should return: 503 when the integration is
	not configured at all, 502 when Google itself failed or answered something
	unusable.
	"""

	def __init__(self, message: str, status_code: int = 502):
		super().__init__(message)
		self.message = message
		self.status_code = status_code


def is_configured() -> bool:
	return bool(settings.GOOGLE_PLACES_API_KEY)


def _api_key() -> str:
	key = settings.GOOGLE_PLACES_API_KEY
	if not key:
		raise GooglePlacesError("Google Places API is not configured.", status_code=503)
	return key


def normalize_place_id(place_id: str) -> str:
	"""Places API (New) sometimes returns ids as 'places/ChIJ...'; the bare id
	is what we store, so normalise on the way in and out."""
	if place_id.startswith("places/"):
		return place_id.split("/", 1)[1]
	return place_id


def _validated_place_id(place_id: str) -> str:
	bare = normalize_place_id((place_id or "").strip())
	if not bare or not _PLACE_ID_RE.match(bare):
		raise GooglePlacesError("Invalid place id.", status_code=400)
	return bare


def autocomplete(body: dict) -> list[dict]:
	"""POST places:autocomplete and return the placePrediction objects.

	`body` is passed through so callers can set their own includedPrimaryTypes,
	locationBias or includedRegionCodes — that part genuinely differs between
	searching for restaurants and searching for cities.
	"""
	key = _api_key()
	try:
		r = requests.post(
			f"{PLACES_API_BASE}/places:autocomplete",
			json=body,
			headers={"Content-Type": "application/json", "X-Goog-Api-Key": key},
			timeout=TIMEOUT_SECONDS,
		)
		r.raise_for_status()
		data = r.json()
	except requests.RequestException as exc:
		logger.exception("Google Places autocomplete failed: %s", exc)
		raise GooglePlacesError("Places API error.") from exc

	return [s["placePrediction"] for s in data.get("suggestions", []) if s.get("placePrediction")]


def details(place_id: str, field_mask: str) -> dict:
	"""GET a single place with the given field mask."""
	key = _api_key()
	bare_id = _validated_place_id(place_id)
	try:
		r = requests.get(
			f"{PLACES_API_BASE}/places/{bare_id}",
			headers={"X-Goog-Api-Key": key, "X-Goog-FieldMask": field_mask},
			timeout=TIMEOUT_SECONDS,
		)
		r.raise_for_status()
		return r.json()
	except requests.RequestException as exc:
		logger.exception("Google Places details failed for %s", bare_id)
		raise GooglePlacesError("Could not verify place with Google.") from exc


def photo_uri(photo_ref: str) -> str:
	"""Resolve a photo resource name to the signed Google CDN URL.

	The caller redirects to it: <img> tags cannot send an Authorization
	header, so the photo endpoint is public and this is the only thing it
	exposes.
	"""
	key = _api_key()
	ref = (photo_ref or "").strip()
	if not ref.startswith("places/"):
		raise GooglePlacesError("Invalid ref.", status_code=400)

	try:
		r = requests.get(
			f"{PLACES_API_BASE}/{ref}/media",
			params={"maxWidthPx": 800, "skipHttpRedirect": "true"},
			headers={"X-Goog-Api-Key": key},
			timeout=TIMEOUT_SECONDS,
		)
		r.raise_for_status()
		data = r.json()
	except requests.RequestException as exc:
		logger.exception("Google Places photo failed for %s", ref)
		raise GooglePlacesError("Places API error.") from exc

	uri = (data.get("photoUri") or "").strip()
	if not uri.startswith("https://"):
		raise GooglePlacesError("Invalid photo URL.")

	host = (urlparse(uri).hostname or "").lower()
	if host not in _ALLOWED_PHOTO_HOSTS and not host.endswith(".googleusercontent.com"):
		raise GooglePlacesError("Untrusted photo host.")

	return uri


def download_photo(uri: str, max_bytes: int) -> tuple[bytes, str]:
	"""Download the bytes of an already-resolved photo URL.

	`photo_uri` is what proves the URL is Google-owned; this re-checks the host
	anyway, because the two calls are separate and a caller could pass anything.
	`max_bytes` is enforced against Content-Length and against what actually
	arrives — a chunked response has no length header to trust.
	"""
	host = (urlparse(uri).hostname or "").lower()
	if host not in _ALLOWED_PHOTO_HOSTS and not host.endswith(".googleusercontent.com"):
		raise GooglePlacesError("Untrusted photo host.")

	try:
		r = requests.get(uri, timeout=TIMEOUT_SECONDS, stream=True)
		r.raise_for_status()

		declared = r.headers.get("Content-Length")
		if declared and declared.isdigit() and int(declared) > max_bytes:
			raise GooglePlacesError("Photo is too large.")

		chunks: list[bytes] = []
		total = 0
		for chunk in r.iter_content(chunk_size=64 * 1024):
			total += len(chunk)
			if total > max_bytes:
				raise GooglePlacesError("Photo is too large.")
			chunks.append(chunk)
	except requests.RequestException as exc:
		logger.exception("Google Places photo download failed for %s", uri)
		raise GooglePlacesError("Places API error.") from exc

	content_type = (r.headers.get("Content-Type") or "").split(";")[0].strip().lower()
	return b"".join(chunks), content_type
