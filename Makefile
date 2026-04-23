.PHONY: setup up down dev frontend logs migrate migrations superuser shell build sync apk

# Primera vez: crea .env, levanta Docker, instala deps frontend
setup:
	cp -n .env.example .env || true
	docker compose -f docker-compose.dev.yml up -d
	cd app && npm install

# Levanta solo Docker (db + backend)
up:
	docker compose -f docker-compose.dev.yml up -d

# Baja Docker
down:
	docker compose -f docker-compose.dev.yml down

# Levanta todo: Docker + frontend (Vite dev server)
dev:
	docker compose -f docker-compose.dev.yml up -d
	cd app && npm run dev -- --open

# Levanta solo el frontend (si Docker ya está corriendo)
frontend:
	cd app && npm run dev -- --open

# Logs de Docker en tiempo real
logs:
	docker compose -f docker-compose.dev.yml logs -f

# Aplica migraciones Django
migrate:
	docker compose -f docker-compose.dev.yml exec backend python manage.py migrate

# Crea migraciones Django
migrations:
	docker compose -f docker-compose.dev.yml exec backend python manage.py makemigrations

# Crea superusuario Django
superuser:
	docker compose -f docker-compose.dev.yml exec -it backend python manage.py createsuperuser

# Shell Django (ipython)
shell:
	docker compose -f docker-compose.dev.yml exec backend python manage.py shell

# Build de produccion del frontend
build:
	cd app && npm run build

# Sincroniza build con Capacitor (Android/iOS)
sync:
	cd app && npx cap sync

# Build + sync apuntando a desarrollo (muse.dothecode.com) — para uso propio
apk:
	cd app && npm run build:apk && npx cap sync

# Build + sync apuntando a produccion (lovemuse.app) — para el cliente / stores
apk-prod:
	cd app && npm run build:apk-prod && npx cap sync

# Carga datos iniciales (cuisines + personas + tags + restaurantes de ejemplo)
seed:
	docker compose -f docker-compose.dev.yml exec backend python manage.py loaddata /app/fixtures/cuisines.json /app/fixtures/personas.json /app/fixtures/tags.json /app/fixtures/seed_restaurants.json

# Tests Django
test:
	docker compose -f docker-compose.dev.yml exec backend python manage.py test
