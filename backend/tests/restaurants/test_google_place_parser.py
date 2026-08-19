"""Tests for the single Google Places parser.

These pin down the two behaviours that differed between the two parsers
this module replaces: which address component wins when several could be
the city, and where the photo proxy URL gets its host from.
"""

import pytest

from restaurants.services import google_place_parser as parser


def test_field_mask_covers_both_former_callers():
	"""The importer's old mask was missing primaryTypeDisplayName, so `type`
	reached the details endpoint but never the database."""
	for field in ("id", "addressComponents", "photos", "primaryTypeDisplayName"):
		assert field in parser.FIELD_MASK


def test_locality_wins_over_admin_area_regardless_of_order():
	"""The old importer loop had `and not city` on the locality branch, so a
	payload listing administrative_area_level_1 first resolved the city to
	the province. Google does not guarantee component order."""
	payload = {
		"addressComponents": [
			{"types": ["administrative_area_level_1"], "longText": "Buenos Aires Province"},
			{"types": ["locality"], "longText": "La Plata"},
		]
	}
	assert parser.parse_place(payload)["city"] == "La Plata"


def test_admin_area_used_when_there_is_no_locality():
	payload = {
		"addressComponents": [
			{"types": ["administrative_area_level_1"], "longText": "Hong Kong Island"},
			{"types": ["country"], "longText": "Hong Kong"},
		]
	}
	parsed = parser.parse_place(payload)
	assert parsed["city"] == "Hong Kong Island"
	assert parsed["country"] == "Hong Kong"


def test_district_comes_from_sublocality():
	"""Both old parsers discarded sublocality, which is exactly the level
	Hong Kong districts live at."""
	payload = {
		"addressComponents": [
			{"types": ["sublocality_level_1", "sublocality"], "longText": "Sheung Wan"},
			{"types": ["locality"], "longText": "Hong Kong"},
		]
	}
	parsed = parser.parse_place(payload)
	assert parsed["district"] == "Sheung Wan"
	assert parsed["city"] == "Hong Kong"


def test_district_is_empty_when_google_does_not_send_one():
	"""Rural areas and unmapped countries have no sublocality. Callers must
	tolerate an empty district rather than get a KeyError."""
	payload = {"addressComponents": [{"types": ["locality"], "longText": "Tandil"}]}
	assert parser.parse_place(payload)["district"] == ""


def test_photo_url_uses_settings_not_request_host(settings):
	"""The old builders used request.build_absolute_uri, so the host of
	whichever request created the row got baked into image_url in the DB."""
	settings.API_PUBLIC_URL = "https://lovemuse.app"
	url = parser.photo_url_for("places/ChIJabc/photos/xyz")
	assert url == "https://lovemuse.app/api/v1/places/photo/?ref=places/ChIJabc/photos/xyz"


def test_photo_url_tolerates_trailing_slash_in_setting(settings):
	settings.API_PUBLIC_URL = "https://lovemuse.app/"
	assert "//api/v1" not in parser.photo_url_for("ref")


def test_image_url_empty_when_place_has_no_photos():
	assert parser.parse_place({"photos": []})["image_url"] == ""


def test_long_values_are_truncated_to_column_limits():
	"""Google occasionally returns strings longer than our columns. Truncating
	at the parser keeps every caller safe instead of only the one that
	remembered to do it."""
	payload = {
		"displayName": {"text": "N" * 500},
		"formattedAddress": "A" * 500,
		"websiteUri": "https://example.com/" + "p" * 600,
		"internationalPhoneNumber": "+" + "9" * 90,
		"addressComponents": [
			{"types": ["locality"], "longText": "C" * 300},
			{"types": ["sublocality"], "longText": "D" * 300},
		],
	}
	parsed = parser.parse_place(payload)
	assert len(parsed["name"]) == 200
	assert len(parsed["address"]) == 300
	assert len(parsed["website"]) == 500
	assert len(parsed["phone"]) == 30
	assert len(parsed["city"]) == 100
	assert len(parsed["district"]) == 120


def test_empty_payload_does_not_raise():
	"""A place with nothing but an id must parse; deciding that a missing
	location is fatal belongs to the persisting caller, not here."""
	parsed = parser.parse_place({})
	assert parsed["lat"] is None
	assert parsed["lng"] is None
	assert parsed["name"] == ""


@pytest.mark.parametrize("blank", [None, ""])
def test_blank_component_text_is_ignored(blank):
	payload = {
		"addressComponents": [
			{"types": ["locality"], "longText": blank},
			{"types": ["postal_town"], "longText": "Reading"},
		]
	}
	assert parser.parse_place(payload)["city"] == "Reading"
