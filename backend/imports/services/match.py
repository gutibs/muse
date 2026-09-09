"""Resuelve una fila del archivo a un restaurante concreto (F2.G).

Segunda de las tres piezas del importador, y la que decide cuánto cuesta un
import. **El orden de los saltos es la feature**:

1. **El catálogo local.** Gratis. A medida que crece, cada import cuesta menos
   que el anterior.
2. **Google**, sólo para lo que no estaba: una llamada de `autocomplete` para
   conseguir el `place_id` y otra de `details` adentro de
   `import_from_google_place_id`.

Google da 1.000 llamadas gratis por SKU y por mes. Un import de 200 filas que
no mire el catálogo primero se come el 40% del cupo mensual, y eso no se nota
hasta que llega la factura.

**Cada fila falla sola.** Un 502 en la fila 12 no puede cancelar las otras 199:
devuelve `ERROR` con su motivo y el despachador sigue. Es la misma lección que
el `render()` fuera del try en F2.E.

Este módulo **crea** el restaurante cuando viene de Google, pero **no crea el
pin**: eso pasa recién cuando la persona confirma. Sumar al catálogo un lugar
real que Google conoce no le hace daño a nadie aunque después se descarte la
fila, y evita pagar la búsqueda dos veces.
"""

import logging
from dataclasses import dataclass
from enum import StrEnum

from places.services import google_places
from restaurants.models import Restaurant
from restaurants.services.google_import import GoogleImportError, import_from_google_place_id

logger = logging.getLogger(__name__)


class MatchOutcome(StrEnum):
	CATALOGUE = "catalogue"
	"""Ya estaba en el catálogo. No costó una llamada."""
	IMPORTED = "imported"
	"""Lo trajo Google y ahora está en el catálogo."""
	NOT_FOUND = "not_found"
	"""Ni el catálogo ni Google lo conocen."""
	AMBIGUOUS = "ambiguous"
	"""Varios candidatos y nada para elegir. No se adivina."""
	ERROR = "error"
	"""Falló la búsqueda. La fila se puede reintentar."""


@dataclass
class MatchResult:
	outcome: MatchOutcome
	restaurant: Restaurant | None = None
	detail: str = ""
	created: bool = False
	"""Este import lo dio de alta en el catálogo.

	No es lo mismo que `IMPORTED`: un lugar que ya estaba con ese `place_id`
	pero cuyo nombre no matcheó también sale por Google, y ése no lo creó
	nadie acá. La diferencia decide quién puede describirlo.
	"""


def match_row(fila: dict, user) -> MatchResult:
	"""Resuelve una fila `{name, city}`. Nunca lanza."""
	nombre = (fila.get("name") or "").strip()
	ciudad = (fila.get("city") or "").strip()
	barrio = (fila.get("district") or "").strip()

	local = _buscar_en_catalogo(nombre, ciudad)
	if local is not None:
		return local

	return _buscar_en_google(nombre, ciudad, barrio, user)


def _buscar_en_catalogo(nombre: str, ciudad: str) -> MatchResult | None:
	"""`None` significa "seguí buscando", no "no existe"."""
	candidatos = list(Restaurant.objects.filter(name__iexact=nombre, is_closed=False)[:5])
	if ciudad:
		candidatos = [r for r in candidatos if _misma_ciudad(r.city, ciudad)]

	encontrados = candidatos[:2]
	if len(encontrados) == 1:
		return MatchResult(MatchOutcome.CATALOGUE, encontrados[0])

	if len(encontrados) > 1:
		# Dos lugares con el mismo nombre y nada que los distinga. Elegir uno
		# al azar le mete a alguien en la cuenta el restaurante equivocado, en
		# otro continente, sin que se entere.
		return MatchResult(
			MatchOutcome.AMBIGUOUS,
			detail=f"{len(encontrados)}+ lugares con ese nombre; falta la ciudad",
		)

	return None


def _misma_ciudad(en_catalogo: str, en_archivo: str) -> bool:
	"""Contención en cualquier dirección, no igualdad.

	El catálogo tiene la misma ciudad escrita de tres formas —"Hong Kong",
	"Hong Kong Island", "Kowloon"— porque `city` sale del payload de Google y
	es texto libre. Exigir igualdad manda a Google filas que ya teníamos, a dos
	llamadas cada una. La contención sigue separando "Hong Kong" de "Tokyo",
	que es lo único que este filtro tiene que garantizar.
	"""
	a = (en_catalogo or "").strip().lower()
	b = (en_archivo or "").strip().lower()
	if not a or not b:
		return False
	return a in b or b in a


def _buscar_en_google(nombre: str, ciudad: str, barrio: str, user) -> MatchResult:
	# El barrio va entre el nombre y la ciudad: es lo que separa dos sucursales
	# del mismo local, que en Hong Kong es la norma y no la excepción.
	consulta = " ".join(parte for parte in (nombre, barrio, ciudad) if parte)
	cuerpo = {"input": consulta, "includedPrimaryTypes": ["restaurant"]}

	try:
		predicciones = google_places.autocomplete(cuerpo)
	except Exception as exc:
		# Ancho a propósito: cualquier cosa que falle acá tiene que quedar
		# contabilizada en la fila y dejar seguir al resto del archivo.
		logger.warning("import: falló la búsqueda de %r: %s", consulta, exc)
		return MatchResult(MatchOutcome.ERROR, detail=str(exc)[:200])

	place_id = _primer_place_id(predicciones)
	if not place_id:
		return MatchResult(MatchOutcome.NOT_FOUND)

	try:
		restaurant, creado = import_from_google_place_id(place_id, user)
	except GoogleImportError as exc:
		logger.warning("import: falló el alta de %s: %s", place_id, exc.message)
		return MatchResult(MatchOutcome.ERROR, detail=exc.message[:200])

	if restaurant.is_closed:
		# `from_google` ya corta los cerrados; acá va lo mismo, para no meter
		# un lugar que no existe más en la lista de alguien.
		return MatchResult(MatchOutcome.NOT_FOUND, detail="el lugar cerró")

	return MatchResult(MatchOutcome.IMPORTED, restaurant, created=creado)


def _primer_place_id(predicciones: list[dict]) -> str:
	"""El `placeId` de la primera predicción, sea cual sea la forma que traiga.

	La API v1 devuelve `placeId`; el shape con `place` ("places/ChIJ…") aparece
	en respuestas de otras rutas. Tolerar las dos evita un import entero en
	blanco por una diferencia de nombre de campo.
	"""
	for prediccion in predicciones or []:
		place_id = prediccion.get("placeId") or ""
		if not place_id and prediccion.get("place"):
			place_id = str(prediccion["place"]).rsplit("/", 1)[-1]
		if place_id:
			return place_id
	return ""
