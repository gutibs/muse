# Muse

## Stack
- **SvelteKit** con adapter-static (SPA) — Svelte 5 runes ($state, $derived, $effect)
- **Tailwind CSS 4** via Vite plugin (sin tailwind.config)
- **Capacitor 8** para Android/iOS
- **Django 5 + DRF** con PostGIS
- **TypeScript** strict

## Estructura
```
muse/
├── app/          # SvelteKit + Capacitor (mobile + web)
├── backend/      # Django + DRF
├── nginx/        # Config prod
└── Makefile      # Comandos de desarrollo
```

## Desarrollo local
- `make setup` — primera vez (levanta Docker + npm install)
- `make dev` — levanta backend (Docker) + frontend (local)
- Backend corre en Docker (PostGIS + Django), frontend corre local (HMR rápido)

## Serialización: camelCase everywhere
El backend usa `djangorestframework-camel-case`:
- Responses llegan en camelCase al frontend
- Requests se envían en camelCase — el parser convierte a snake_case
- Serializers usan snake_case normal

## Mobile-First — OBLIGATORIO

### Safe areas
- AppShell.svelte es el ÚNICO componente que aplica padding de safe-area
- NUNCA poner safe-area padding en componentes individuales
- Variables CSS: `--sat`, `--sab`, `--sal`, `--sar`

### Layout de pantallas
```svelte
<header class="shrink-0">...</header>
<main class="flex-1 overflow-y-auto">...</main>
<nav class="shrink-0">...</nav>
```

### Reglas estrictas
- `h-full` NUNCA `h-screen` — falla en móvil con barras dinámicas
- Scroll SIEMPRE dentro de `<main>`, nunca en body
- Touch targets: `min-h-11 min-w-11` (44px mínimo)
- Inputs: `text-base` mínimo (16px, evita auto-zoom en iOS)
- NO usar `hover:` para indicar interactividad
- Feedback táctil: `active:scale-95` o `active:opacity-80`
- NO usar `100vh` — usar `100dvh` o `h-full` con flex
- NO usar `position: fixed` sin considerar safe areas
- NO usar tooltips — usar labels visibles o bottom sheets

### Phone frame (web preview)
En pantallas > 480px se muestra un frame de celular simulado (390x844px).
NO afecta el build de Capacitor.

## Infraestructura AWS (producción)

- **EC2** `t3.small` Ubuntu 24.04 — IP fija `3.129.56.80`
- **RDS** `db.t3.micro` PostgreSQL 16 — endpoint `database-1.c1yuu8ceyjpj.us-east-2.rds.amazonaws.com`
- **Security Group EC2** (`muse-ec2-sg`): puertos 22 (0.0.0.0/0), 80, 443 — el 22 abierto a todos es intencional para GitHub Actions
- **Security Group RDS** (`muse-rds-sg`): puerto 5432 solo desde `muse-ec2-sg`
- **Deploy automático**: push a `main` → GitHub Actions → SSH al EC2 → `docker-compose up --build`
- **Secrets en GitHub**: `EC2_HOST`, `EC2_SSH_KEY` (clave `~/.ssh/id_ed25519` del EC2)
- **Variables de entorno**: en `/home/ubuntu/muse/.env` en el servidor (no en el repo)
- **Pendiente**: dominio + SSL con Certbot + actualizar ALLOWED_HOSTS y CORS

## Convenciones
- Indentación con tabs
- Comillas simples en JS/TS
- Componentes: PascalCase (`AppShell.svelte`)
- Servicios/utils: kebab-case con sufijo (`.service.ts`, `.store.svelte.ts`)
- Imports: usar `$lib/` siempre
