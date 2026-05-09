#!/usr/bin/env bash
# Reject console.log( in app/src/ files. Compiled chunks under
# app/ios/App/App/public/ and app/android/app/src/main/assets/public/ are
# excluded by pre-commit's `files:` filter, but we re-check defensively.
set -euo pipefail

rc=0
for path in "$@"; do
	case "$path" in
		app/ios/*|app/android/*|*/dist/*|*/.svelte-kit/*|*/build/*)
			continue
			;;
	esac
	# Strip line comments before grep so `// console.log(...)` isn't flagged.
	# Pattern matches `console.log(` not preceded by `//` on the same line.
	if grep -nE '(^|[^/])console\.log\(' "$path" >/dev/null 2>&1; then
		grep -nE '(^|[^/])console\.log\(' "$path" \
			| sed "s|^|$path:|" >&2
		rc=1
	fi
done

if [ "$rc" -ne 0 ]; then
	echo "" >&2
	echo "console.log() found in source. Use a structured logger or remove." >&2
fi
exit "$rc"
