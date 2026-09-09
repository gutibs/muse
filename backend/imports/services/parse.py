"""Convierte el archivo que sube la persona en filas utilizables.

Primera de las tres piezas del importador y la única que no habla con nadie:
entra un archivo, salen filas `{name, city, row}`. Todo lo que pueda fallar por
la forma del archivo falla acá, **antes de gastar una sola llamada a Google**.

Dos formatos, y ninguno necesita pandas: CSV con la stdlib y `.xlsx` con
`openpyxl`. Son archivos de 200 filas; traer numpy entero para leer dos columnas
sería absurdo.

**Un archivo malo cancela; una fila mala no.** Alguien que exporta 200 lugares y
tiene 3 filas rotas tiene que poder importar las otras 197, y enterarse de cuáles
fallaron. Sólo se aborta cuando no hay ninguna columna de nombre, porque ahí no
queda nada que buscar.
"""

import csv
import io

from django.utils.translation import gettext_lazy as _

# Los encabezados con los que la gente exporta de verdad. Nadie tiene un archivo
# con las columnas que uno esperaba, y pedirle que lo renombre antes de subirlo
# es perder a la mitad en el primer paso.
COLUMNAS_NOMBRE = {
	"name",
	"nombre",
	"restaurant",
	"restaurante",
	"title",
	"titulo",
	"título",
	"place",
	"lugar",
}
COLUMNAS_CIUDAD = {"city", "ciudad", "town", "location", "ubicacion", "ubicación"}
# Las etiquetas con las que se describe un lugar. Los slugs son únicos en toda
# la tabla `Tag`, así que no hace falta saber de qué eje viene cada uno.
# El barrio. En Hong Kong es como la gente ubica un lugar, y es lo único que
# distingue dos sucursales del mismo nombre cuando se le pregunta a Google.
COLUMNAS_BARRIO = {"district", "neighbourhood", "neighborhood", "barrio", "area", "zona"}
COLUMNAS_TAGS = {"tags", "tag", "etiquetas", "vibe", "occasion", "scene", "dietary"}

EXTENSIONES = {".csv", ".xlsx"}
MAX_FILAS = 500


class ParseError(Exception):
	"""El archivo entero no se puede leer. Distinto de una fila que falla."""


def parse_file(archivo) -> tuple[list[dict], list[dict]]:
	"""Devuelve `(filas, errores)`. Lanza `ParseError` si el archivo no sirve."""
	nombre = (getattr(archivo, "name", "") or "").lower()
	extension = nombre[nombre.rfind(".") :] if "." in nombre else ""

	if extension not in EXTENSIONES:
		raise ParseError(_("Only .csv and .xlsx files can be imported."))

	crudas = _leer_xlsx(archivo) if extension == ".xlsx" else _leer_csv(archivo)
	if not crudas:
		raise ParseError(_("The file has no rows."))

	cabecera, *cuerpo = crudas
	columnas = _ubicar_columnas(cabecera)
	indice_nombre = columnas["name"]
	indice_ciudad = columnas["city"]
	if indice_nombre is None:
		raise ParseError(
			_("The file needs a column with the restaurant name (name, nombre, restaurant…).")
		)

	filas: list[dict] = []
	errores: list[dict] = []

	for numero, cruda in enumerate(cuerpo, start=2):
		nombre_lugar = _celda(cruda, indice_nombre)
		ciudad = _celda(cruda, indice_ciudad) if indice_ciudad is not None else ""

		# Una fila entera en blanco es ruido de exportación, no un error de la
		# persona: Excel las agrega sola al final. No se cuenta ni se reporta.
		if not any(_celda(cruda, i) for i in range(len(cruda))):
			continue

		if not nombre_lugar:
			errores.append({"row": numero, "reason": "missing_name"})
			continue

		filas.append(
			{
				"name": nombre_lugar,
				"city": ciudad,
				"district": _celda(cruda, columnas["district"]),
				"tags": _etiquetas(cruda, columnas["tags"]),
				"row": numero,
			}
		)

	return filas[:MAX_FILAS], errores


def _leer_csv(archivo) -> list[list[str]]:
	crudo = archivo.read()
	if isinstance(crudo, bytes):
		# `utf-8-sig` y no `utf-8`: Excel guarda los CSV con BOM, y sin esto la
		# primera columna se llama "﻿name" y el archivo entero parece no
		# tener nombres.
		texto = crudo.decode("utf-8-sig", errors="replace")
	else:
		texto = crudo

	if not texto.strip():
		return []

	# Punto y coma es lo que exporta Excel donde la coma es separador decimal.
	try:
		dialecto = csv.Sniffer().sniff(texto[:2048], delimiters=",;\t")
	except csv.Error:
		dialecto = csv.excel

	return list(csv.reader(io.StringIO(texto), dialecto))


def _leer_xlsx(archivo) -> list[list[str]]:
	import openpyxl

	try:
		libro = openpyxl.load_workbook(archivo, read_only=True, data_only=True)
	except Exception as exc:
		raise ParseError(_("That .xlsx file could not be read.")) from exc

	hoja = libro.active
	return [["" if celda is None else str(celda) for celda in fila] for fila in hoja.values]


def _ubicar_columnas(cabecera: list[str]) -> dict[str, int | None]:
	columnas: dict = {"name": None, "city": None, "district": None, "tags": []}
	for i, celda in enumerate(cabecera):
		clave = (celda or "").strip().lower()
		if columnas["name"] is None and clave in COLUMNAS_NOMBRE:
			columnas["name"] = i
		elif columnas["city"] is None and clave in COLUMNAS_CIUDAD:
			columnas["city"] = i
		elif columnas["district"] is None and clave in COLUMNAS_BARRIO:
			columnas["district"] = i
		elif clave in COLUMNAS_TAGS:
			columnas["tags"].append(i)
	return columnas


def _etiquetas(fila: list[str], indices: list[int]) -> list[str]:
	"""Separadas por coma, normalizadas a slug. Sin resolver contra la base:
	esto no sabe qué etiquetas existen, sólo qué escribió la persona.

	Puede venir una sola columna `tags` o una por eje (`vibe`, `occasion`…):
	todas se juntan en la misma lista porque los slugs son únicos en toda la
	tabla y no hay forma de que dos ejes se pisen.
	"""
	etiquetas = []
	for indice in indices:
		crudo = _celda(fila, indice)
		etiquetas += [_slug(parte) for parte in crudo.split(",") if parte.strip()]
	return etiquetas


def _slug(texto: str) -> str:
	return "-".join(texto.strip().lower().split())


def _celda(fila: list[str], indice: int) -> str:
	if indice is None or indice >= len(fila):
		return ""
	return (fila[indice] or "").strip()
