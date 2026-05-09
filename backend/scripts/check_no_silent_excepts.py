#!/usr/bin/env python3
"""Reject `except: pass` / `except Exception: pass|continue` clauses.

Pre-commit hook. Receives a list of files via argv. Parses each as Python and
walks AST looking for ExceptHandler bodies that consist of a single `pass`
or `continue` (no log, no re-raise, no other statement).

Allowed: any except clause that does *something* — even a one-line log.
"""

from __future__ import annotations

import ast
import sys


def _is_silent_body(body: list[ast.stmt]) -> bool:
	if len(body) != 1:
		return False
	stmt = body[0]
	return isinstance(stmt, ast.Pass | ast.Continue)


def check_file(path: str) -> list[tuple[int, str]]:
	"""Return list of (line, message) for offending except clauses."""
	try:
		with open(path, encoding="utf-8") as f:
			source = f.read()
	except (OSError, UnicodeDecodeError):
		return []
	try:
		tree = ast.parse(source, filename=path)
	except SyntaxError:
		return []

	offenders: list[tuple[int, str]] = []
	for node in ast.walk(tree):
		if isinstance(node, ast.ExceptHandler) and _is_silent_body(node.body):
			exc_label = "except:"
			if node.type is not None:
				exc_label = f"except {ast.unparse(node.type)}:"
			body_kw = "pass" if isinstance(node.body[0], ast.Pass) else "continue"
			offenders.append((node.lineno, f"{exc_label} {body_kw}"))
	return offenders


def main(argv: list[str]) -> int:
	rc = 0
	for path in argv[1:]:
		for line, snippet in check_file(path):
			print(
				f"{path}:{line}: silent except clause ({snippet}) — " "log the error or re-raise.",
				file=sys.stderr,
			)
			rc = 1
	return rc


if __name__ == "__main__":
	sys.exit(main(sys.argv))
