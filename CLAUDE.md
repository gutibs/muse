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
│   ├── tests/    # pytest + factory_boy (18 archivos en disco, 51 tests, 35 críticos)
│   │             # ojo: feed/test_prune_activity.py no está commiteado
│   └── scripts/  # hooks custom de pre-commit
├── nginx/        # Config prod
└── Makefile
```

## Desarrollo local
- `make setup` — primera vez (Docker + npm install)
- **`cp app/.env.example app/.env`** la primera vez. Vite resuelve `envDir`
  contra `app/`, así que el `.env` de la raíz —que configura el backend— no lo
  lee. Sin ese archivo el frontend le pide la API al dev server de Vite y todas
  las pantallas muestran "Something went wrong" con el backend perfectamente
  sano. `api.service.ts` avisa por consola si falta.
- `make dev` — backend en Docker (PostGIS+Django) + frontend local (HMR)
- Tests backend: `docker compose -f docker-compose.dev.yml run --rm backend pytest tests/`
  - **`make test` NO corre esto**: su target usa `python manage.py test` (runner de Django),
    que ignora `pytest.ini` y los marcadores `@pytest.mark.critical`. Si querés la suite de
    verdad, usá el comando de arriba.
- Pre-commit: `pre-commit install` la primera vez. Después corre solo en cada commit.

## Probar con datos reales
- `make prod-snapshot` — baja el último backup de producción, lo restaura en la
  base local y **anonimiza los usuarios en el mismo paso** (emails a
  `@local.test`, contraseña `local-dev-1234` para todas las cuentas). Te deja
  los ~550 restaurantes y sus pins reales sin datos personales encima.
- **No apuntar el entorno local a RDS.** `pytest --create-db` crea y borra
  bases, un `migrate` distraído modifica producción, y los seeds de demo
  insertarían 500 restaurantes falsos en el catálogo real. El script y
  `anonymise_local_data` abortan si `DB_HOST` no es local.
- Tests que hablan con Google de verdad: `pytest -m integration`. Se saltean
  solos sin `GOOGLE_PLACES_API_KEY`, así que CI queda verde sin credenciales.
  Existen porque la suite entera estuvo en verde mientras las fotos no
  funcionaban en producción: los mocks devolvían lo que el código esperaba y
  Google no.

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
- **Rating: resuelto.** `RatingHearts.svelte` es el display de sólo lectura,
  `RatingStars.svelte` el input, `HeartIcon.svelte` el glifo — único lugar con el
  `<path>` del SVG. `escapeHtml` también está en un solo lugar
  (`lib/utils/escape-html.ts`). El path del SVG llegó a estar pegado en 17 lugares:
  no lo vuelvas a pegar.
- **Leaflet: resuelto.** `lib/utils/map.ts` es el único lugar que carga la librería
  (`loadLeaflet`, que además trae el CSS) y el único que crea mapas con los defaults
  del proyecto (`createMap`, con la URL de tiles de cartocdn y la atribución de
  CARTO/OSM). `PinsMap.svelte`, `MapView.svelte`, `LocationPicker.svelte` y
  `map/+page.svelte` pasan todos por ahí. Antes eran tres bootstraps con la URL de
  tiles pegada en cada uno, y `LocationPicker` había derivado sin `minZoom`,
  `maxBounds`, `noWrap` ni atribución. **No hagas `import('leaflet')` a mano en una
  vista nueva** — pedí el namespace a `loadLeaflet()`.

## Frontend que solo lee la primera página (resuelto, con una excepción deliberada)
- El backend pagina con PAGE_SIZE=20. Hay **dos** formas de consumir un listado y
  la elección es explícita:
  - `pinsService.list()` → una página (`PaginatedResponse`). Para infinite scroll,
    como lo hace `feed/+page.svelte`.
  - `pinsService.listAll()` → todos los resultados, siguiendo `next` vía
    `api.getAll` (con tope de páginas para no colgar la UI ante una respuesta rota).
    Para pantallas que necesitan el set completo.
- `map/+page.svelte` y `restaurant/[id]/+page.svelte` usan `listAll()`. Antes leían
  sólo la primera página: el mapa dibujaba 20 markers como máximo, y `restaurant/[id]`
  buscaba tu pin dentro de esos 20 — con 21+ pins te mostraba "Agregar a mis pins"
  en vez de "Editar" y el backend contestaba 409 al tocarlo.
- `profile/+page.svelte:125` usa `list()` **a propósito**: muestra la primera página
  y el total real sale de `res.count`, que el backend calcula sobre el filtro
  completo. No es el bug de arriba.
- Si agregás un listado nuevo, elegí una de las dos y dejá dicho por qué. Lo que no
  va es leer `res.results` de una sola página y tratarlo como si fuera todo.

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

Producción corre en **EC2 + RDS en AWS**, dominio `lovemuse.app`, deploy por GitHub Actions
al hacer push a `main`. El detalle —IPs, endpoints, security groups, secrets y los tres
gotchas del deploy que ya rompieron el sitio— está en **`docs/INFRA.md`**. Leelo antes de
desplegar o de diagnosticar una caída.

Lo único que hay que saber de memoria: **en el deploy, `build` va primero, con los
contenedores todavía arriba, y recién después `down` + `up -d`.** Al revés, un build roto
deja producción caída.

---

# APK / Android

El procedimiento completo de release —elegir el número de versión, los dos archivos que hay
que actualizar en el mismo commit, el build contra producción y la regeneración de los 24
iconos de launcher— está en la skill **`/release-apk`** de este proyecto
(`.claude/skills/release-apk/`). Invocala cuando toque compilar o publicar.

Lo único que hay que saber de memoria: **para distribución siempre `npm run build:apk-prod`,
nunca `build:apk`** — el segundo apunta a `muse.dothecode.com`, que es la URL de dev.

---

# Diagnóstico de bugs

Aplica la regla de evidencia global (ver `~/.claude/CLAUDE.md`): sin log, response real o
consola, es hipótesis y se etiqueta como tal.

Lo específico de Muse, que es donde más se falla:

- **No asumas que el usuario tiene un APK viejo, caché vieja o el env equivocado.** Puede ser
  cualquiera de las tres y es tentador cerrarlo así. Preguntá qué `versionName` muestra la app
  y comparalo con el `versionName` actual de `build.gradle` antes de tocar código.
- Si el síntoma se parece a un bug conocido del audit, verificá que sea el mismo. Los de
  paginación y los tres bootstraps de Leaflet se parecen entre sí y no son lo mismo.
