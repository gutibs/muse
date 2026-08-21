"""Single field mask + single parser for Google Places responses.

Before this module the parsing lived in two places that had already
diverged: `places/views.py::place_details` asked Google for 10 fields,
`google_import._FIELD_MASK` asked for the same 9 minus
`primaryTypeDisplayName` — so `place_details` could return a `type` that
the importer never saw and therefore never reached the database. The
`addressComponents` loop was written twice with different precedence
rules, which meant the two modules could return different cities for the
same place depending on the order Google happened to send the components
in.

Everything that reads a Google Places payload goes through here. Adding a
field is a one-file change.
"""

from __future__ import annotations

from django.conf import settings

from places.services.google_places import normalize_place_id

# Every field any caller needs. One mask: a caller that needs a new field
# adds it here, and both the details endpoint and the importer see it.
FIELD_MASK = ",".join(
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
		# Atributos de atmósfera. Suben la llamada al SKU "Enterprise +
		# Atmosphere", que cuesta $25 por mil contra $20 del anterior — y
		# cero en la práctica: el cap gratuito es de 1.000 llamadas por SKU
		# por mes y la caché de 30 días deja el techo del catálogo en ~550.
		# Verificado contra la doc oficial y una llamada real (2026-08-19).
		# Google avisa cuando un lugar cerró. Sin este campo, dos
		# restaurantes estuvieron cuatro años cerrados en el catálogo sin que
		# nadie se enterara.
		"businessStatus",
		"outdoorSeating",
		"liveMusic",
		"allowsDogs",
	]
)

# Atributo del payload → slug del catálogo. Sólo van los que tienen una
# etiqueta que ya existe: inferir una que no está en el catálogo dejaría un
# chip marcado apuntando a la nada.
_INFERRED_TAGS = {
	"outdoorSeating": "outdoor-terrace",
	"liveMusic": "live-music",
	"allowsDogs": "pet-friendly",
}


def inferred_tag_slugs(payload: dict) -> set[str]:
	"""Etiquetas que se desprenden de lo que Google afirma del local.

	Sólo con `True` explícito. `False` es una respuesta —Google sabe que no
	tiene terraza— y la ausencia del campo es otra —no sabe—: en los dos
	casos no se marca nada, porque una sugerencia equivocada es peor que
	ninguna.

	Función pura: no toca la red ni la base, así se puede probar cualquier
	combinación con un payload de mentira.
	"""
	return {slug for campo, slug in _INFERRED_TAGS.items() if payload.get(campo) is True}


# Address component types we care about, most specific first. Google does
# not guarantee the order of `addressComponents`, so precedence has to be
# resolved after collecting them all — the old loops resolved it by
# whichever component happened to come first.
_CITY_TYPES = ("locality", "postal_town", "administrative_area_level_1")
_DISTRICT_TYPES = (
	"sublocality_level_1",
	"sublocality",
	"neighborhood",
	"administrative_area_level_2",
)


def photo_url_for(place_id: str) -> str:
	"""Absolute URL to our own photo proxy for a place.

	Se arma con el **place_id** y no con el nombre de recurso de la foto: ese
	ref caduca, y esta URL se persiste en `Restaurant.image_url`. Las URLs que
	llevaban el ref quedaron muertas en producción cuando los refs vencieron
	(`400 INVALID_ARGUMENT`), y no había forma de recuperarlas sin reescribir
	la columna.

	Absoluta porque se persiste. Construida desde settings y no con
	`request.build_absolute_uri` para que el valor guardado no dependa de por
	qué host entró el request que creó la fila.
	"""
	base = getattr(settings, "API_PUBLIC_URL", "http://localhost:8001").rstrip("/")
	return f"{base}/api/v1/places/photo/?place={place_id}"


def _components_by_type(payload: dict) -> dict[str, str]:
	"""Flatten addressComponents into {type: longText}.

	First occurrence of each type wins, which only matters for duplicated
	types; precedence between different types is decided by the caller.
	"""
	out: dict[str, str] = {}
	for comp in payload.get("addressComponents") or []:
		text = comp.get("longText", "") or ""
		if not text:
			continue
		for type_name in comp.get("types") or []:
			out.setdefault(type_name, text)
	return out


def _first_of(components: dict[str, str], types: tuple[str, ...]) -> str:
	for type_name in types:
		if components.get(type_name):
			return components[type_name]
	return ""


def parse_place(payload: dict) -> dict:
	"""Normalize a Google Places payload into our own vocabulary.

	Returns every field we extract, including ones no model column holds
	yet (`district`, `type`). Callers take what they need. Values are
	truncated to our column limits here — Google occasionally returns
	strings longer than they should be, and truncating at the boundary
	keeps every caller safe instead of only the one that remembered.

	`lat`/`lng` are returned as-is (possibly None); building a Point is the
	persisting caller's job, since only it knows whether a missing location
	is fatal.
	"""
	location = payload.get("location") or {}
	components = _components_by_type(payload)
	hours = payload.get("regularOpeningHours") or {}

	photo_ref = ""
	photos = payload.get("photos") or []
	if photos:
		photo_ref = photos[0].get("name", "") or ""

	# El id llega como 'ChIJ...' o como 'places/ChIJ...' según el endpoint.
	place_id = normalize_place_id(payload.get("id") or "")

	return {
		"place_id": place_id,
		"name": ((payload.get("displayName") or {}).get("text", "") or "")[:200],
		"address": (payload.get("formattedAddress", "") or "")[:300],
		"city": _first_of(components, _CITY_TYPES)[:100],
		"district": _first_of(components, _DISTRICT_TYPES)[:120],
		# Sólo el cierre definitivo. `CLOSED_TEMPORARILY` reabre, y un lugar
		# que reabre tiene que volver a aparecer solo.
		"is_closed": payload.get("businessStatus") == "CLOSED_PERMANENTLY",
		"country": components.get("country", "")[:100],
		"lat": location.get("latitude"),
		"lng": location.get("longitude"),
		"website": (payload.get("websiteUri", "") or "")[:500],
		"phone": (payload.get("internationalPhoneNumber", "") or "")[:30],
		"photo_ref": photo_ref,
		"image_url": (photo_url_for(place_id) if (photo_ref and place_id) else "")[:2000],
		"opening_hours": hours.get("weekdayDescriptions", []) or [],
		"type": ((payload.get("primaryTypeDisplayName") or {}).get("text", "") or ""),
	}
