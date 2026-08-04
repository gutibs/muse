# Muse

App social de pin/visita/compartir restaurantes con amigos. Modelo central:
cada usuario marca restaurantes como `visited` (con rating + comentario) o
`to_visit`, ve la actividad de sus amigos en un feed; las listas se pueden
compartir por link público.

## Stack
- **SvelteKit** adapter-static (SPA) — Svelte 5 runes (`$state`, `$derived`, `$effect`)
- **Tailwind CSS 4** vía Vite plugin (sin `tailwind.config`)
- **Capacitor 8** para Android/iOS
- **Django 5 + DRF + PostGIS** — JWT (simplejwt), `djangorestframework-camel-case`
- **TypeScript** strict

## Estructura
```
muse/
├── app/          # SvelteKit + Capacitor
├── backend/      # Django + DRF
│   ├── tests/    # pytest + factory_boy (17 archivos, 58 tests, 35 críticos)
│   └── scripts/  # hooks custom de pre-commit
├── nginx/        # Config prod
└── Makefile
```

## Desarrollo local
- `make setup` — primera vez (Docker + npm install)
- `make dev` — backend en Docker (PostGIS+Django) + frontend local (HMR)
- Tests backend: `docker compose -f docker-compose.dev.yml run --rm backend pytest tests/`
- Pre-commit: `pre-commit install` la primera vez. Después corre solo en cada commit.

---

# Reglas chequeadas por tooling

Estas las valida el harness antes de que llegues a CI. Si algo de acá entra
a `main` es porque alguien hizo `--no-verify` (no lo hagas).

## Backend — `pre-commit` (ver `.pre-commit-config.yaml`)
- **`ruff`** sobre `backend/`. Reglas activas (`backend/pyproject.toml`):
  - `E F W I N UP B A C4` — pyflakes + pep8 + naming + pyupgrade + bugbear + builtins + comprehensions
  - **`DTZ`** — `datetime.now()` sin `tz` es error.
  - **`T20`** — `print()` debug es error. Usar `logger.<level>(...)` (excepción: `tests/`, `manage.py`, `scripts/`).
- **`ruff-format`** — formatting con tabs (convención del proyecto).
- **`check_no_silent_excepts.py`** — rechaza `except: pass` y `except Exception: pass|continue`.
  Cualquier acción en el body (incluso un `logger.warning(...)` de una línea) es suficiente.

## Frontend — `pre-commit`
- **`check_no_console_log.sh`** — rechaza `console.log(` en `app/src/`. Excluye explícitamente
  los chunks compilados de Capacitor (`app/ios/...`, `app/android/...`) — son falsos positivos.
- **No hay** lint/format automático del frontend hoy. Si tocás `.svelte`/`.ts`, las convenciones
  de la sección "Aspiracional" abajo no las enforza nadie.

## Repo entero
- **`gitleaks`** — secretos hardcoded (AWS keys, tokens, etc.). Usa el ruleset por defecto.
  Algunos placeholders conocidos (ej. `AKIAIOSFODNN7EXAMPLE`) están allowlisted upstream — no
  los uses para "probar el hook"; tomá un valor random que matchee el regex.

## Tests del path crítico (`backend/tests/`)
35 tests marcados `@pytest.mark.critical`. Los que cubren invariantes que no
podés romper sin romper el producto:
  - `are_friends` simétrico y solo cuenta `ACCEPTED`; `friend_ids` idem
  - `RegisterView` crea Profile vía signal, consume `EmailInvitation` y
    persiste los `ConsentRecord` (GDPR + PDPO)
  - `PinSerializer.validate` (status ↔ rating) y el 409 al pinear dos veces
  - `from_google` race → un único Restaurant en DB
  - `SharedListPublicView` 404 en token inactivo/inválido y **no expone el
    email del dueño** (endpoint anónimo)
  - Borrado de cuenta: exige contraseña, anonimiza conservando reseñas,
    borra el grafo social, invalida los JWT vigentes
- **Cualquier cambio en `accounts/`, `pins/`, `restaurants/from_google` debe correr la suite.**
  Si rompiste alguno, el bug está en tu cambio.
- **Corré con `--create-db`.** `pytest.ini` trae `--reuse-db`: al agregar una
  migración, la base reusada queda con el schema al día pero sin los datos que
  siembran las data migrations, y te da 5 rojos que no tienen nada que ver con
  tu cambio.

---

# Convenciones aspiracionales

No las chequea nadie. Si una de estas se rompe en prod silenciosamente, el
camino correcto es convertirla en lint/test, no agregarle más prosa acá.

## Mobile-first (frontend)
Todas las reglas siguientes son aspiracionales. La forma de "chequearlas" hoy
es leer el código y preguntar a Claude. Si alguna es realmente crítica para
el producto, conviene un test visual o un eslint-plugin custom.

- **Safe areas**: `AppShell.svelte` es el ÚNICO componente que aplica padding
  de safe-area. Variables CSS: `--sat`, `--sab`, `--sal`, `--sar`. Nunca
  duplicar el padding en componentes hijos.
- **Layout de pantalla**:
  ```svelte
  <header class="shrink-0">...</header>
  <main class="flex-1 overflow-y-auto">...</main>
  <nav class="shrink-0">...</nav>
  ```
- `h-full`, NUNCA `h-screen` — fail con barras dinámicas en móvil.
- `100dvh` o `h-full` con flex, NUNCA `100vh`.
- Scroll dentro de `<main>`, nunca en `body`.
- Touch targets: `min-h-11 min-w-11` (44px mínimo iOS HIG).
- Inputs: `text-base` mínimo (16px) — evita auto-zoom iOS.
- NO `hover:` para indicar interactividad (no existe en móvil). Usar
  `active:scale-95` o `active:opacity-80` para feedback táctil.
- NO `position: fixed` sin considerar safe areas.
- NO tooltips — usar labels visibles o bottom sheets.
- Phone frame en pantallas web > 480px (390x844px). NO afecta build de Capacitor.

## Naming y estructura (frontend)
- Componentes: **PascalCase** (`AppShell.svelte`).
- Servicios/utils/stores: **kebab-case con sufijo** (`.service.ts`, `.store.svelte.ts`, `.svelte.ts`).
- Imports: usar `$lib/` siempre (nunca paths relativos largos).
- Comillas simples en JS/TS. (Aspiracional — no hay prettier config.)
- Tabs para indentación. (Backend lo enforza ruff-format; frontend depende del editor.)

## Serialización: camelCase everywhere
- DRF usa `djangorestframework-camel-case`.
- Responses → camelCase al frontend.
- Requests → frontend manda camelCase, parser convierte a snake_case.
- Serializers internos → snake_case normal.
- El parser tolera ambos en input (ej: `placeId` y `place_id` aceptados en `from_google`).

## Auth y permisos (backend)
- DRF default `IsAuthenticated`. Endpoints públicos son la excepción explícita
  (`AllowAny` + throttle por scope).
- Filtrar siempre por `user=request.user` en `get_queryset` cuando el dato es
  per-user (`PinViewSet`, `SharedListViewSet`, `FriendshipViewSet` ya lo hacen).
- Friendship lookups: usar `_are_friends(a, b)` de `accounts/views.py`. Es
  simétrico y filtra `ACCEPTED`.
- Throttles por scope en `settings.py`: `login`, `register`, `user_search`,
  `places`, `invite`. Si agregás un endpoint sensible, agregá scope acá y
  marcalo en la view.

## Logging
- Backend: `logger = logging.getLogger(__name__)` por archivo. Para errores
  de integración usar `logger.exception(...)` con contexto (place_id, user_id, etc.).
- Frontend: hoy hay catches mudos en varios `+page.svelte` (ver "Patrones a
  evitar" abajo). La intención es una util `logSilent(scope, err)` que vaya
  a `console.warn` siempre. Pendiente.

---

# Patrones a evitar (aprendizajes del audit)

Cosas que el audit (`AUDIT_QUALITATIVE.md`) detectó. Cada bullet existe en
el código real hoy o existió hasta hace poco — no son hipotéticos.

## `django.core.mail.send_mail` directo
- El envío de emails transaccionales pasa **siempre** por
  `accounts.services.email.send_invitation_email` (y futuros `send_*_email`).
  Razón: ese service centraliza Resend, templates, logging estructurado y
  el manejo de `EmailSendError`. Llamar a `django.core.mail.send_mail` directo
  esquiva todo eso (sin tracking, sin retry, sin templates compartidos). La
  excepción legítima es Django admin (password reset interno) — para eso
  podés dejar el SMTP backend configurado en `settings.py`. Para CUALQUIER
  email que recibe un usuario del producto, va por el service.

## Validación duplicada modelo+serializer
- `Pin.clean()` y `PinSerializer.validate` chequean lo mismo (status↔rating).
  La del modelo **sí corre**: `Pin.save()` llama `full_clean(validate_unique=False)`.
  El `validate_unique=False` no es opcional — con la validación de unicidad
  activada, pinear dos veces lanzaba el `ValidationError` de Django antes del
  INSERT, DRF no lo traduce, y el usuario recibía un 500 en lugar del 409 que
  `PinViewSet.create` intenta dar. Cuando agregues validación, ponela en UN
  solo lugar (preferentemente el serializer, que es por donde entra HTTP).

## Reimplementar Leaflet o el ícono de rating en cada vista
- Ya existen `lib/components/PinsMap.svelte`, `lib/utils/escape-html.ts` y
  `lib/utils/map-popup.ts`. **Usalos**; no agregues una vista con su propio
  bootstrap de Leaflet ni otra copia de `escapeHtml`.
- Para rating: `RatingHearts.svelte` es el display de sólo lectura,
  `RatingStars.svelte` el input, `HeartIcon.svelte` el glifo. El path del SVG
  llegó a estar pegado en 17 lugares — no lo vuelvas a pegar.

## Frontend que solo lee la primera página (VIGENTE, 2 lugares)
- `profile/+page.svelte:125` y `restaurant/[id]/+page.svelte:34` llaman
  `pinsService.list()` y usan sólo `res.results`, sin seguir la paginación. El
  backend pagina con PAGE_SIZE=20.
- El de `restaurant/[id]` es el que muerde primero: busca el pin propio del
  restaurante dentro de la primera página. Con 21+ pins, un restaurante que ya
  pineaste muestra "Agregar a mis pins" en vez de "Editar"; al tocarlo, el
  backend responde 409 porque el pin existe. El 409 ahora está bien formado
  (trae `pinId`), pero el frontend no lo usa para redirigir.
- Si agregás listados largos, **paginá o usá infinite scroll** desde el
  principio.

## CharField libre cuando hay un set finito de valores
- Ya resuelto para dietary: `Profile.dietary_preferences` es M2M a
  `DietaryPreference` (set cerrado, seedeado por migración), y los tags de
  `MenuItem` son M2M con `Tag`. **El patrón queda como regla**: campo con set
  finito → `TextChoices` o FK, nunca texto libre que el frontend rellena.

## Geocoding sin proxy
- `LocationPicker.svelte` pegaba directo a Nominatim sin User-Agent custom.
  Ya está detrás de `ReverseGeocodeView`. **Cualquier llamada a un servicio
  externo desde el frontend tiene que ir por backend** — hoy Google Places va
  por `places/services/google_places.py` y Nominatim por `places/views.py`.

## Catches mudos
- En backend lo enforza el hook `check_no_silent_excepts`. En frontend usá
  `logSilent(scope, err)` de `lib/utils/logger.ts` — ya está adoptado en todos
  los catches menos uno (descartar el share sheet rechaza con `AbortError`, o
  sea que dispara en una cancelación normal y logearlo sería ruido; el
  comentario lo aclara ahí mismo).
- Un catch que muestra un mensaje al usuario **igual necesita log**: sin traza
  en consola, un reporte de "no me carga X" no tiene evidencia que mirar.

## Hardcodear cosas que deberían ser env
- `SECRET_KEY`, `GOOGLE_PLACES_API_KEY`, URLs públicas, credenciales SMTP — todo
  por env. `backend/config/settings.py` ya tiene el patrón
  `os.environ.get("X", default)`. Vars nuevas: actualizar `.env.example` en
  el mismo commit.

## Textos legales duplicados
- Los textos legales viven **sólo** en `nginx/landing/*.html` (en/es/it). La
  app no lleva copia: linkea a las URLs públicas desde `app/src/lib/legal.ts`.
  Cuando estaban en los dos lados divergieron sin que nadie lo notara —la app
  unificó GDPR+PDPO y la landing no—, así que la política que veías dependía
  de por dónde entrabas. `docs/GDPR_PRIVACY_POLICY.md` es borrador interno,
  **no** lo que se publica.

## Reglas escritas que nadie chequea
- Esta sección entera podría ser tests visuales o lint custom. La regla:
  **si una convención es realmente crítica, conviértela en check; si no,
  aceptá que se va a violar.** No agregar más prosa a este archivo esperando
  que sirva como enforcement.

---

# Servicios canónicos del backend

Lugares únicos donde vive lógica que tiende a duplicarse si la dejás suelta
en views/serializers. Si vas a agregar algo que pisa una de estas
responsabilidades, **usá el service existente** o ampliáslo — no rearmes
una segunda implementación al lado.

| Responsabilidad | Módulo canónico | Notas |
|---|---|---|
| Hablar con Google Places (HTTP) | `places/services/google_places.py` | Único lugar que usa la API key y maneja errores de `requests`. Valida el `place_id` antes de interpolarlo en la URL. |
| Importar/normalizar restaurantes desde Google | `restaurants/services/google_import.py` | Parseo + race condition de doble alta (D-002). El HTTP lo delega al cliente de arriba. |
| Email transaccional al usuario (invitations) | `accounts/services/email.py::send_invitation_email` | Envuelve Resend. Lanza `EmailSendError(status_code=502/503)`. Templates en `backend/templates/emails/invitation.{es,en,it}.{html,txt}`. |
| Amistades (simétrico, sólo ACCEPTED) | `accounts/services/friendships.py` | `are_friends(a, b)` y `friend_ids(user)`. No cuentan PENDING ni DECLINED. Reusalos en cualquier filtro nuevo de "datos de amigos" — el set de ids estuvo duplicado en dos módulos por no existir el helper. |
| Borrado de cuenta (GDPR art. 17) | `accounts/services/account_deletion.py::anonymise_user` | Anonimiza, no borra: las reseñas sobreviven sin identidad (D-009). Atómico. |
| Parseo de coordenadas de query params | `places/geo.py` | `parse_lat_lng` y `parse_radius_km`. Lanzan `ValidationError` de DRF → 400. |

Cuando agregues un service nuevo:
- Vive en `<app>/services/<scope>.py` (mismo patrón que los de arriba).
- Funciones puras (sin estado de instancia) salvo que haya razón clara.
- Excepciones custom con contexto suficiente (status code sugerido, mensaje
  con detalle) — no `raise Exception(...)` desnudo.
- Tests con mock al boundary externo (Google API, Resend SDK, etc.), no a
  internals del service. Patrón: ver `tests/accounts/test_invitation_email.py`
  y `tests/restaurants/test_from_google_race.py`.

---

# Infraestructura

## Producción (estado actual)
- **EC2** `t3.small` Ubuntu 24.04 — IP fija `3.129.56.80`, disco raíz 20 GiB
  (era 8 GiB y se llenó el 2026-08-04: el deploy murió en el `git pull` y el
  sitio quedó caído. Si volvés a rozar el límite, mirá `/var/lib/containerd`.)
- **RDS** `db.t3.micro` PostgreSQL 16 — endpoint `database-1.c1yuu8ceyjpj.us-east-2.rds.amazonaws.com`
- **SG EC2** (`muse-ec2-sg`): 22 (0.0.0.0/0 — intencional para GitHub Actions), 80, 443
- **SG RDS** (`muse-rds-sg`): 5432 solo desde `muse-ec2-sg`
- **Dominio y SSL**: `lovemuse.app` con Certbot, servido por nginx (`nginx/default-aws.conf`).
- **Deploy**: push a `main` → GitHub Actions → SSH al EC2. El orden importa:
  **`build` primero, con los contenedores todavía arriba; recién después
  `down` + `up -d`.** Al revés (que era como estaba), cualquier fallo del build
  dejaba producción caída. `set -e` corta antes del `down`, así que un build
  roto es un deploy en rojo con el sitio intacto.
  - Bug conocido de docker-compose 1.29.2: hacer `down && up`, nunca solo `up`.
  - `command_timeout: 30m` en la acción SSH: un build sin cache no entra en los
    10 minutos por defecto y la sesión se corta a mitad de camino.
  - El prune de imágenes va **al final y con `--filter until=720h`**. Un
    `docker image prune -af` sin filtro se lleva las capas intermedias sin tag
    de las que depende el cache del builder clásico (compose v1 no usa
    BuildKit) y fuerza un build completo en el deploy siguiente.
- **Secrets en GitHub**: `EC2_HOST`, `EC2_SSH_KEY`
- **Vars de entorno**: en `/home/ubuntu/muse/.env` en el server (no en el repo)
- **Pendiente**: la imagen del backend instala `requirements/dev.txt` (pytest,
  ipython, debug-toolbar viajan a producción y pesan ~1.75 GB).

## APK
- Build prod: `npm run build:apk-prod` (usa `.env.capacitor-prod` → `lovemuse.app`)
- NUNCA `build:apk` para distribución (apunta a `muse.dothecode.com`, dev URL)
- **El APK V1.0.0 compilado es anterior al borrado de cuenta.** Play Store lo
  exige para toda app con registro, así que hace falta rebuildear antes de
  publicar (sería `V1.1.0`: feature visible al usuario).

### Versionado APK — convención `V<major>.<minor>.<patch>`
Toda release del APK lleva un version humano en formato `V<major>.<minor>.<patch>`:
- **`major`** (ej: `0` → `1`) — release mayor: rompe compatibilidad o pivote de producto.
- **`minor`** (ej: `0` → `1`) — important release: feature visible al usuario, cambio de
  endpoint, cambio de assets que afecta UX (icono, splash, naming).
- **`patch`** (ej: `0` → `1`) — bugfix sobre el `minor` actual.

Cómo aplicarla en cada build:
1. Antes de buildear, **leer `app/android/app/build.gradle`** para ver el `versionName` actual.
2. Decidir el siguiente número según las reglas de arriba (no inventar saltos: `V0.1.3` después
   de `V0.1.2`, no `V0.2.0` salvo que el cambio sea claramente "important").
3. Actualizar **en el mismo commit**:
   - `app/android/app/build.gradle` → `versionName "V0.1.0"` y `versionCode N+1` (entero
     monotónico, lo exige Play Store).
   - `app/package.json` → `"version": "0.1.0"` (sin la `V`, npm exige semver).
4. Buildear con `npm run build:apk-prod` desde `app/`.

Regla derivada: el `versionName` es la fuente de verdad humana. Si el celu de un usuario muestra
"V0.1.0" pero el APK actual es "V0.1.2", hay un APK viejo instalado — desinstalar y reinstalar
antes de seguir diagnosticando.

### Iconos de launcher (Android)
- Source de marca: `app/src/lib/assets/logo_muse.png`.
- Asset destino: `app/android/app/src/main/res/mipmap-{ldpi,mdpi,hdpi,xhdpi,xxhdpi,xxxhdpi}/`
  con `ic_launcher.png`, `ic_launcher_round.png` y `ic_launcher_foreground.png`.
- Background del adaptive icon: `app/src/main/res/values/ic_launcher_background.xml` (hoy `#FFFFFF`).
- Si actualizás el logo, regenerá los 18 assets — no los edites a mano densidad por densidad.

---

# Diagnóstico de bugs: con evidencia, no por adivinación

Regla dura. Si un usuario reporta un error:
1. **Antes** de proponer la causa, juntar evidencia concreta del flujo que el usuario está viendo:
   logs del servidor, response real del endpoint, mensaje de consola, network tab, payload exacto.
2. Reproducir el caso si se puede (`curl` al endpoint con los mismos datos, abrir el flujo en local).
3. Solo después de tener evidencia, decir "el bug es X". Hasta entonces son hipótesis y se etiquetan
   como tales ("posible causa", "hipótesis a verificar").

**Anti-patrones explícitos que esto prohíbe:**
- Decir "Encontrado" cuando solo hiciste una inferencia plausible.
- Asumir que el cliente está usando un APK viejo, una caché vieja, o env equivocado, sin
  verificar (preguntando o inspeccionando lo que efectivamente está corriendo).
- Saltar a "ya sé qué es" porque el síntoma se parece a un bug anterior conocido.
- Cerrar un ticket con "no puedo reproducir" sin mostrar qué pasos se ejecutaron.

**Por qué:** las inferencias rápidas mandan al usuario a perseguir un fantasma. Cuesta menos
preguntar "¿qué versión tenés instalada?" o pedir el log que reescribir un fix sobre una causa
errónea.
