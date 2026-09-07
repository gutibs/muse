"""Leer el archivo que sube la persona y sacar filas utilizables (F2.G).

El parseo es la primera de las tres piezas del importador y la única que no
habla con nadie: entra un archivo, salen filas `{name, city}`. Todo lo que
pueda fallar acá —una columna que se llama distinto, una fila vacía, un BOM de
Excel, un separador con punto y coma— falla antes de gastar una sola llamada a
Google.

**Las filas malas no cancelan el archivo.** Alguien que exporta 200 lugares y
tiene 3 filas rotas tiene que poder importar las otras 197: el error va por
fila, con su motivo, no por archivo.
"""

import io

import pytest

from imports.services.parse import ParseError, parse_file


def _csv(texto: str, nombre: str = "lista.csv") -> io.BytesIO:
	archivo = io.BytesIO(texto.encode("utf-8"))
	archivo.name = nombre
	return archivo


def test_lee_un_csv_con_nombre_y_ciudad():
	filas, errores = parse_file(_csv("name,city\nYardbird,Hong Kong\nAnchoita,Buenos Aires\n"))
	assert [f["name"] for f in filas] == ["Yardbird", "Anchoita"]
	assert filas[0]["city"] == "Hong Kong"
	assert errores == []


def test_la_ciudad_es_opcional():
	"""Google encuentra igual con el nombre solo; la ciudad ayuda a desambiguar."""
	filas, _ = parse_file(_csv("name\nYardbird\n"))
	assert filas[0]["name"] == "Yardbird"
	assert filas[0]["city"] == ""


def test_acepta_los_nombres_de_columna_que_usa_la_gente():
	"""Nadie exporta un archivo con las columnas que uno esperaba."""
	for cabecera in ("name,city", "Name,City", "nombre,ciudad", "restaurant,city", "title,city"):
		filas, errores = parse_file(_csv(f"{cabecera}\nYardbird,Hong Kong\n"))
		assert filas and filas[0]["name"] == "Yardbird", cabecera
		assert errores == []


def test_un_archivo_sin_columna_de_nombre_no_se_puede_leer():
	"""Es el único error que sí cancela: sin nombre no hay nada que buscar."""
	with pytest.raises(ParseError):
		parse_file(_csv("direccion,telefono\nAlgo,123\n"))


def test_las_filas_vacias_se_saltean_sin_romper():
	filas, errores = parse_file(_csv("name,city\nYardbird,Hong Kong\n,\n\nAnchoita,\n"))
	assert [f["name"] for f in filas] == ["Yardbird", "Anchoita"]
	assert errores == []


def test_una_fila_sin_nombre_es_un_error_de_esa_fila_y_nada_mas():
	filas, errores = parse_file(_csv("name,city\nYardbird,Hong Kong\n,Roma\nAnchoita,\n"))
	assert [f["name"] for f in filas] == ["Yardbird", "Anchoita"]
	assert len(errores) == 1
	assert errores[0]["row"] == 3


def test_limpia_los_espacios_de_los_bordes():
	filas, _ = parse_file(_csv("name,city\n  Yardbird  ,  Hong Kong  \n"))
	assert filas[0] == {"name": "Yardbird", "city": "Hong Kong", "row": 2}


def test_soporta_el_bom_que_mete_excel():
	"""Excel guarda los CSV con BOM, y sin esto la primera columna se llama
	`\\ufeffname` y el archivo entero parece no tener nombres."""
	archivo = io.BytesIO("﻿name,city\nYardbird,Hong Kong\n".encode())
	archivo.name = "lista.csv"
	filas, errores = parse_file(archivo)
	assert filas[0]["name"] == "Yardbird"
	assert errores == []


def test_soporta_punto_y_coma_como_separador():
	"""Es lo que exporta Excel en configuraciones regionales con coma decimal."""
	filas, _ = parse_file(_csv("name;city\nYardbird;Hong Kong\n"))
	assert filas[0]["name"] == "Yardbird"
	assert filas[0]["city"] == "Hong Kong"


def test_un_archivo_vacio_avisa():
	with pytest.raises(ParseError):
		parse_file(_csv(""))


def test_un_xlsx_se_lee_igual_que_un_csv():
	openpyxl = pytest.importorskip("openpyxl")
	libro = openpyxl.Workbook()
	hoja = libro.active
	hoja.append(["name", "city"])
	hoja.append(["Yardbird", "Hong Kong"])
	hoja.append([None, None])
	hoja.append(["Anchoita", "Buenos Aires"])

	buffer = io.BytesIO()
	libro.save(buffer)
	buffer.seek(0)
	buffer.name = "lista.xlsx"

	filas, errores = parse_file(buffer)
	assert [f["name"] for f in filas] == ["Yardbird", "Anchoita"]
	assert errores == []


def test_una_extension_que_no_conocemos_avisa():
	with pytest.raises(ParseError):
		parse_file(_csv("lo que sea", nombre="lista.pdf"))
