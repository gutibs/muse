#!/usr/bin/env bash
#
# Chequea qué sirve el nginx de producción en cada ruta.
#
# El riesgo que cubre: `default-aws.conf` decide, con cuatro regex, qué es la
# landing, qué es la SPA y qué es un 404. Un cambio de una letra en cualquiera
# de ellas puede exponer la app entera por web o dejar las listas compartidas
# en 404, y nada más lo verifica.
#
# Levanta la imagen real con el conf real —bajado a HTTP porque los certs de
# Let's Encrypt no existen fuera del EC2— y le pega a cada ruta.
#
#   ./nginx/test-routes.sh
#
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK="$(mktemp -d)"
IMAGE="muse-nginx-routes-test"
CONTAINER="muse-nginx-routes-test"
PORT="${PORT:-8099}"
BASE="http://localhost:${PORT}"
# Generado en cada corrida y no hardcodeado: el token real es un uuid4 y así
# se prueba la regex con uno distinto cada vez (además de que un literal con
# esta pinta hace saltar a gitleaks).
SHARE_UUID="$(python3 -c 'import uuid; print(uuid.uuid4())')"

cleanup() {
	docker rm -f "$CONTAINER" >/dev/null 2>&1 || true
	docker rmi -f "$IMAGE" >/dev/null 2>&1 || true
	rm -rf "$WORK"
}
trap cleanup EXIT

echo "==> Compilando la SPA (mismo stage que la imagen de producción)"
docker build --quiet --target frontend -f "$REPO_ROOT/nginx/Dockerfile.aws" -t "${IMAGE}-frontend" "$REPO_ROOT" >/dev/null
docker create --name "${CONTAINER}-extract" "${IMAGE}-frontend" >/dev/null
docker cp "${CONTAINER}-extract:/app/build" "$WORK/app" >/dev/null
docker rm -f "${CONTAINER}-extract" >/dev/null

echo "==> Preparando el conf real, bajado a HTTP"
python3 - "$REPO_ROOT/nginx/default-aws.conf" "$WORK/test.conf" <<'PY'
import re
import sys

src = open(sys.argv[1]).read()
# Sólo el server de HTTPS: es el que tiene los locations. Los certs no existen
# acá, y el upstream `backend` tampoco, así que ambos se neutralizan. Todo lo
# demás queda literal — el punto es probar el archivo que va a producción.
conf = src[src.index("# HTTPS"):]
conf = conf.replace("listen 443 ssl;", "listen 80;")
conf = re.sub(r"\tssl_certificate.*\n", "", conf)
conf = conf.replace("server_name lovemuse.app www.lovemuse.app;", "server_name localhost;")
conf = conf.replace("http://backend:8000", "http://127.0.0.1:9999")
open(sys.argv[2], "w").write(conf)
PY

cp -R "$REPO_ROOT/nginx/landing" "$WORK/landing"
cat > "$WORK/Dockerfile" <<'DOCKER'
FROM nginx:alpine
COPY test.conf /etc/nginx/conf.d/default.conf
COPY landing/ /usr/share/nginx/landing/
COPY app/ /usr/share/nginx/app/
DOCKER

docker build --quiet -t "$IMAGE" "$WORK" >/dev/null
docker run -d --name "$CONTAINER" -p "${PORT}:80" "$IMAGE" >/dev/null

for _ in $(seq 1 20); do
	if curl -fsS -o /dev/null "${BASE}/" 2>/dev/null; then break; fi
	sleep 0.5
done

failures=0
check() {
	local path="$1" expected="$2" what="$3"
	local got
	got="$(curl -s -o /dev/null -w '%{http_code}' "${BASE}${path}")"
	if [ "$got" = "$expected" ]; then
		printf '  ok    %-46s %s  (%s)\n' "$path" "$got" "$what"
	else
		printf '  FALLA %-46s esperado %s, dio %s  (%s)\n' "$path" "$expected" "$got" "$what"
		failures=$((failures + 1))
	fi
}

echo "==> Rutas"
check "/"                       200 "landing"
check "/privacy.html"           200 "legales, única copia publicada"
check "/shared/${SHARE_UUID}"        200 "lista compartida servida por la SPA"
check "/shared/${SHARE_UUID}/"       200 "idem con barra final"
check "/favicon.svg"            200 "favicon de la SPA"
check "/shared/abc"             404 "token corto: no es un uuid"
check "/shared/"                404 "sin token"
check "/feed"                   404 "la app NO se sirve por web"
check "/login"                  404 "la app NO se sirve por web"
check "/profile"                404 "la app NO se sirve por web"

echo "==> La ruta compartida devuelve el index de la SPA, no otra cosa"
body="$(curl -s "${BASE}/shared/${SHARE_UUID}")"
if echo "$body" | grep -q '_app/immutable/entry/start'; then
	echo "  ok    el HTML es el bundle de SvelteKit"
else
	echo "  FALLA el HTML no parece el index de la SPA"
	failures=$((failures + 1))
fi

asset="$(echo "$body" | grep -o '/_app/immutable/entry/start[^"]*' | head -1)"
cache="$(curl -s -o /dev/null -w '%header{Cache-Control}' "${BASE}${asset}")"
if echo "$cache" | grep -q immutable; then
	echo "  ok    los assets con hash salen inmutables ($cache)"
else
	echo "  FALLA los assets deberían ser inmutables, salieron: $cache"
	failures=$((failures + 1))
fi

if [ "$failures" -gt 0 ]; then
	echo "==> $failures chequeo(s) fallaron"
	exit 1
fi
echo "==> Todo bien"
