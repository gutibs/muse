#!/usr/bin/env python3
"""Cada versión de política tiene que apuntar a un texto que exista.

Hook de pre-commit. `POLICY_VERSIONS` (backend/accounts/services/consent.py)
estampa una fecha en cada `ConsentRecord`: es la forma de saber *a qué texto*
dijo que sí una persona. Si la fecha no coincide con la del documento publicado
en `nginx/landing/`, esa evidencia señala un documento que nadie puede leer.

Pasó de verdad el 2026-09-08: se bumpeó TERMS a 2026-09-08 junto con GDPR y
PDPO, pero `terms.html` no se tocó y siguió diciendo 18 de mayo.

Vive acá y no en pytest porque el contenedor del backend sólo monta `backend/`:
desde ahí `nginx/landing/` no existe. El hook corre en el repo entero.

DIGEST no se chequea: es una finalidad que se acepta, no un documento.
"""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
CONSENT = REPO / "backend" / "accounts" / "services" / "consent.py"

# Qué documento publicado respalda cada política.
DOCUMENTOS = {
	"GDPR": "gdpr.html",
	"PDPO": "pdpo.html",
	"TERMS": "terms.html",
}

MESES = (
	"January February March April May June July August September October November December"
).split()

FECHA_PUBLICADA = re.compile(r"Last updated:\s*(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})")


def versiones_declaradas() -> dict[str, str]:
	"""Lee POLICY_VERSIONS del AST, sin importar Django."""
	arbol = ast.parse(CONSENT.read_text(encoding="utf-8"))
	for nodo in ast.walk(arbol):
		if not isinstance(nodo, ast.Assign):
			continue
		if not any(getattr(t, "id", None) == "POLICY_VERSIONS" for t in nodo.targets):
			continue
		versiones = {}
		for clave, valor in zip(nodo.value.keys, nodo.value.values, strict=True):
			# ConsentRecord.Policy.GDPR -> "GDPR"
			versiones[clave.attr] = valor.value
		return versiones
	return {}


def fecha_del_documento(nombre: str) -> str | None:
	texto = (REPO / "nginx" / "landing" / nombre).read_text(encoding="utf-8")
	m = FECHA_PUBLICADA.search(texto)
	if not m:
		return None
	dia, mes, anio = m.groups()
	if mes not in MESES:
		return None
	return f"{anio}-{MESES.index(mes) + 1:02d}-{int(dia):02d}"


def main() -> int:
	problemas = []
	declaradas = versiones_declaradas()
	if not declaradas:
		print("No se pudo leer POLICY_VERSIONS de consent.py", file=sys.stderr)
		return 1

	for politica, documento in DOCUMENTOS.items():
		declarada = declaradas.get(politica)
		if declarada is None:
			continue
		publicada = fecha_del_documento(documento)
		if publicada is None:
			problemas.append(f"{documento}: no se encontró un 'Last updated' legible")
		elif publicada != declarada:
			problemas.append(
				f"{politica}: POLICY_VERSIONS dice {declarada} y "
				f"nginx/landing/{documento} dice {publicada}"
			)

	if problemas:
		print("Versiones de política que no apuntan al texto publicado:", file=sys.stderr)
		for p in problemas:
			print(f"  - {p}", file=sys.stderr)
		print(
			"\nUna versión que no existe deja la evidencia del consentimiento "
			"señalando un documento que nadie puede leer.",
			file=sys.stderr,
		)
		return 1
	return 0


if __name__ == "__main__":
	sys.exit(main())
