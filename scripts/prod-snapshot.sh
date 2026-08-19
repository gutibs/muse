#!/usr/bin/env bash
#
# Trae el último backup de producción a la base local y lo anonimiza.
#
# El objetivo es desarrollar contra datos parecidos a los reales —los 557
# restaurantes, sus pins, sus relaciones— sin apuntar el entorno local a RDS.
# Apuntar a RDS parece más simple y es mucho peor: `pytest --create-db` crea y
# borra bases, un `migrate` distraído modifica producción, los seeds de demo
# insertarían 500 restaurantes falsos en el catálogo real, y habría que abrirle
# el security group de RDS a una IP doméstica que cambia sola.
#
# La anonimización no es opcional ni un segundo paso: corre acá adentro, antes
# de que la base quede utilizable.
#
#   ./scripts/prod-snapshot.sh
#
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

SSH_HOST="${MUSE_SSH_HOST:-muse}"
# Se puede pasar un override con MUSE_COMPOSE_FILES: en esta máquina el 5433 lo
# ocupa la base de otro proyecto, y un override con `ports: !reset []` deja
# levantar la de Muse sin conflicto.
COMPOSE_DEV="docker compose ${MUSE_COMPOSE_FILES:--f docker-compose.dev.yml}"
COMPOSE_PROD="sudo docker-compose -f docker-compose.aws.yml"
DUMP="$(mktemp -t muse-snapshot).sql.gz"
trap 'rm -f "$DUMP"' EXIT

# --- 1. Confirmar que la base local es local ------------------------------
DB_HOST_LOCAL="$(grep -E '^[[:space:]]*DB_HOST=' .env 2>/dev/null | tail -1 | cut -d= -f2 | tr -d ' ' || true)"
case "$DB_HOST_LOCAL" in
	db|localhost|127.0.0.1|"")
		;;
	*)
		echo "ABORTA: DB_HOST del .env es '$DB_HOST_LOCAL', que no es local." >&2
		echo "Este script borra y recrea la base entera." >&2
		exit 1
		;;
esac

# --- 2. Bajar el dump más reciente ----------------------------------------
echo "==> Buscando el backup más reciente en el EC2"
ULTIMO="$(ssh "$SSH_HOST" "cd /home/ubuntu/muse && $COMPOSE_PROD exec -T db sh -c 'ls -1t /backups/muse-*.sql.gz | head -1'" | tr -d '\r')"
if [ -z "$ULTIMO" ]; then
	echo "ABORTA: no hay backups en /backups del contenedor db." >&2
	exit 1
fi
echo "    $ULTIMO"

echo "==> Descargando"
ssh "$SSH_HOST" "cd /home/ubuntu/muse && $COMPOSE_PROD exec -T db sh -c 'cat $ULTIMO'" > "$DUMP"
echo "    $(wc -c < "$DUMP" | tr -d ' ') bytes"

# --- 3. Recrear la base local ---------------------------------------------
echo "==> Recreando la base local"
$COMPOSE_DEV up -d db >/dev/null 2>&1
$COMPOSE_DEV exec -T db sh -c 'until pg_isready -U "$POSTGRES_USER" -d postgres >/dev/null 2>&1; do sleep 1; done'
# WITH (FORCE) cierra las conexiones abiertas: sin eso, un runserver que quedó
# corriendo impide el DROP y el script muere a la mitad.
$COMPOSE_DEV exec -T db sh -c 'psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d postgres \
	-c "DROP DATABASE IF EXISTS $POSTGRES_DB WITH (FORCE)" \
	-c "CREATE DATABASE $POSTGRES_DB OWNER $POSTGRES_USER"'

echo "==> Restaurando"
gunzip -c "$DUMP" | $COMPOSE_DEV exec -T db sh -c 'psql -q -U "$POSTGRES_USER" -d "$POSTGRES_DB"' > /dev/null

# --- 4. Poner el schema al día y anonimizar -------------------------------
# El dump puede ser anterior a la última migración.
echo "==> Migrando"
$COMPOSE_DEV run --rm -T backend python manage.py migrate --noinput | tail -2

echo "==> Anonimizando"
$COMPOSE_DEV run --rm -T backend python manage.py anonymise_local_data | tail -3

echo
echo "==> Listo: datos de producción, usuarios inventados."
