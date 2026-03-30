.PHONY: setup up down dev logs migrate migrations superuser shell build sync

setup:
	cp -n .env.example .env || true
	docker compose up -d
	cd app && npm install

up:
	docker compose up -d

down:
	docker compose down

dev:
	docker compose up -d
	cd app && npm run dev -- --open

logs:
	docker compose logs -f

migrate:
	docker compose exec backend python manage.py migrate

migrations:
	docker compose exec backend python manage.py makemigrations

superuser:
	docker compose exec -it backend python manage.py createsuperuser

shell:
	docker compose exec backend python manage.py shell

build:
	cd app && npm run build

sync:
	cd app && npx cap sync
