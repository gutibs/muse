#!/usr/bin/env python3
"""El español de Muse no vosea.

Hook de pre-commit. Existe porque la regla escrita no alcanzó: el commit que
sacó el voseo dejó restos, y el 2026-09-08/09 aparecieron en **tres lugares
distintos** —el catálogo del backend ("Revisá tu correo"), los documentos
legales publicados ("de tú", "a tú") y la app ("Subí una planilla... vos
elegís")—. Las tres veces se encontraron mirando una pantalla, de casualidad,
nunca leyendo un diff.

Busca formas verbales concretas, no un patrón genérico: una lista explícita da
muchos menos falsos positivos que "palabra terminada en vocal acentuada", que
marcaría `está`, `acá`, `café` y medio diccionario.

Cubre:
  - `app/src/lib/i18n/translations.ts`, **sólo el bloque `es:`** (el italiano
    comparte terminaciones y no tiene por qué pasar por acá).
  - `backend/locale/es/LC_MESSAGES/django.po`, sólo las líneas `msgstr`.
  - `nginx/landing/*.html` entero: ninguna forma de esta lista existe en
    inglés ni en italiano, así que no hace falta delimitar el bloque.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

# Imperativos y presentes del voseo. En singular y con la forma que de verdad
# se escribe en la app; el chequeo es case-insensitive sólo en la inicial.
FORMAS = (
	# imperativos
	"subí elegí revisá activá tocá mirá probá contá agregá buscá guardá compartí "
	"escribí poné andá vení hacé decí pedí seguí creá instalá completá ingresá "
	"confirmá verificá intentá volvé sacá cargá enviá abrí cerrá dejá llevá "
	"marcá tomá usá cambiá borrá invitá aceptá sumá fijate acordate quedate "
	"publicá calificá valorá seleccioná descargá actualizá sincronizá reportá "
	"bloqueá denunciá compará esperá revisalo mandá pasá dejalo mirala "
	# presentes
	"querés tenés podés sabés elegís vivís venís decís hacés ponés sos vas "
	"necesitás preferís buscás guardás compartís"
).split()

# El pronombre suelto. "a vos", "de vos", "vos elegís".
PRONOMBRE = re.compile(r"\bvos\b", re.IGNORECASE)

PATRON = re.compile(r"\b(" + "|".join(f"{f[0].upper()}{f[1:]}|{f}" for f in FORMAS) + r")\b")

REPO = Path(__file__).resolve().parents[2]


def lineas_del_bloque_es(texto: str) -> list[tuple[int, str]]:
	"""Sólo el bloque `es:` de translations.ts."""
	lineas = texto.splitlines()
	dentro = False
	salida = []
	for numero, linea in enumerate(lineas, 1):
		if re.match(r"^\tes: \{", linea):
			dentro = True
			continue
		if dentro and re.match(r"^\t(en|it): \{", linea):
			break
		if dentro:
			salida.append((numero, linea))
	return salida


def revisar(path: Path) -> list[str]:
	if not path.exists():
		return []
	texto = path.read_text(encoding="utf-8")

	if path.name == "translations.ts":
		candidatas = lineas_del_bloque_es(texto)
	elif path.suffix == ".po":
		candidatas = [
			(numero, linea)
			for numero, linea in enumerate(texto.splitlines(), 1)
			if linea.startswith("msgstr")
		]
	else:
		candidatas = list(enumerate(texto.splitlines(), 1))

	problemas = []
	for numero, linea in candidatas:
		hallazgos = PATRON.findall(linea) + PRONOMBRE.findall(linea)
		if hallazgos:
			relativa = path.relative_to(REPO)
			problemas.append(f"  {relativa}:{numero}: {', '.join(sorted(set(hallazgos)))}")
	return problemas


def main() -> int:
	objetivos = [
		REPO / "app" / "src" / "lib" / "i18n" / "translations.ts",
		REPO / "backend" / "locale" / "es" / "LC_MESSAGES" / "django.po",
		*sorted((REPO / "nginx" / "landing").glob("*.html")),
	]

	problemas = [p for objetivo in objetivos for p in revisar(objetivo)]
	if problemas:
		print("El español de Muse no vosea, y esto sí:", file=sys.stderr)
		print("\n".join(problemas), file=sys.stderr)
		print(
			"\nUsá la forma de tuteo: 'sube', 'quieres', 'tú eliges', 'envía'.",
			file=sys.stderr,
		)
		return 1
	return 0


if __name__ == "__main__":
	sys.exit(main())
