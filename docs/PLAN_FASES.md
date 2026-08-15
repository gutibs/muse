# Plan de desarrollo — Fase 1 (beta) y Fase 2 (full build)

Estado: aprobado para arrancar el 2026-08-15. Alcance completo de las dos fases.
Base: intercambio de emails con Jess (2026-08-03 → 2026-08-15) + review de código
multi-agente sobre el repo real (11 agentes, todo verificado con `file:line`).

Las fechas y la facturación se manejan fuera de este documento.

---

## Decisiones de arquitectura tomadas

Estas condicionan todo lo demás y no se revisan por feature.

1. **Taxonomía unificada en `Tag`, con los tres ejes colgando del `Pin`.**
   `Tag.Kind` se extiende con `vibe` / `occasion` / `scene`; `Persona` se migra a
   `Tag(kind=occasion)` con data migration; `Pin.tags` reemplaza a `Pin.personas`.
   Razón: hoy son dos modelos en dos apps con semánticas distintas (Vibe es del
   Restaurant, Occasion es del Pin), y con el vibe global dos usuarios con opinión
   distinta se pisan mutuamente sin historial. Además `_check_owner_or_staff`
   (`restaurants/views.py:83`) da 403 al PATCH de un restaurante ajeno, así que con
   el vibe en el Restaurant sólo el creador podría etiquetarlo. El vibe agregado del
   restaurante se deriva de los pins, no se almacena.

2. **La SPA se sirve en web, sólo en las rutas públicas.**
   `nginx/Dockerfile.aws` gana un stage de node; `nginx/default-aws.conf` gana
   `location` explícitos para `/shared/`, `/u/` y `/vote/`; el `return 404` sigue
   cubriendo todo lo demás. `nginx/landing/shared.html` (318 líneas de JS vanilla con
   su propio i18n) se borra. Razón: sin esto, cada superficie pública nueva se
   escribe dos veces con dos sistemas de i18n — el mecanismo exacto que hizo divergir
   los textos legales.

3. **Las fotos cacheadas viven en S3 detrás de CloudFront, con TTL de 30 días.**
   No en el disco del EC2: el contenedor `backend` de `docker-compose.aws.yml` no
   declara volumes y el deploy hace `down --remove-orphans` + `up -d`, así que todo
   lo escrito al filesystem se borra en cada push a main. El TTL de 30 días no es
   una elección de performance: los Google Maps Platform Terms permiten cachear
   Place IDs indefinidamente pero el resto del contenido hasta 30 días.

4. **Redis entra en el bloque de cimientos, no cuando haga falta una cola.**
   Hoy no hay bloque `CACHES` en `settings.py`, así que Django cae a `LocMemCache`
   por proceso con 3 workers de gunicorn: los 8 scopes de throttle cuentan por worker
   (`places: 120/hour` es en la práctica ~360/hour) y se resetean en cada deploy.
   Redis arregla la caché de Places y el throttling en el mismo movimiento.

---

## Bloque 0 — Cimientos

**Ninguna feature arranca antes que esto.** No es refactor por prolijidad: son los
módulos únicos que las features de las dos fases van a consumir. Construidas sin
ellos, cada feature multiplica la duplicación que ya existe. Como efecto colateral
cierra tres bugs vigentes en producción.

### 0.1 — `restaurants/services/google_place_parser.py`

Un field mask y un parser, reemplazando los dos que ya divergieron:
`places/views.py:270-283` pide 10 campos, `google_import.py:27-39` pide los mismos
9 menos `primaryTypeDisplayName`; el loop de `addressComponents` está escrito dos
veces (`places/views.py:292-299` vs `google_import.py:91-98`) y difieren — el
importador tiene el guard `and not city` y la view no, así que con dos componentes
`locality` los dos módulos devuelven ciudades distintas para el mismo place.

- Deja de descartar `sublocality` (de ahí sale el distrito).
- Absorbe `photo_url_for(ref)`, hoy copiado en `places/views.py:307` y
  `restaurants/views.py:148-151`, tomando la base de `settings.APP_PUBLIC_URL` en
  vez de `build_absolute_uri` — hoy el host del request queda horneado dentro de
  `Restaurant.image_url` en la DB.
- `place_details` pasa a ser sólo serialización de lo que devuelve el parser.
- `image_url` va a `read_only_fields` en `restaurants/serializers.py:96-103`: hoy es
  escribible por el cliente, así que la misma columna puede contener nuestro proxy o
  cualquier URL que un usuario haya mandado.

Consumidores: `places/views.py`, `google_import.py`, y después el importador.

### 0.2 — Infra: Redis + S3/CloudFront

- Bloque `CACHES` en `settings.py` + `redis` en `requirements/base.txt` + servicio en
  `docker-compose.aws.yml` y `docker-compose.dev.yml`, con `maxmemory-policy
  allkeys-lru` y TTL explícito por clave.
- `boto3` + `django-storages`, bucket S3 y distribución CloudFront.
- **Arreglar de paso los avatares**, que ya están rotos en prod: `MEDIA_ROOT`
  (`settings.py:111`) sólo se sirve con `DEBUG` (`config/urls.py:15-16`) y
  `default-aws.conf` no tiene `location /media/`. Con S3 el problema desaparece.
- `settings.APP_PUBLIC_URL` como única fuente de la base pública.

### 0.3 — `accounts/services/visibility.py` y `pins/selectors.py`

- `can_view(viewer, owner)` y `visible_user_ids(viewer)`, hermanos de
  `friendships.py` (mismo patrón: funciones puras). Hoy el chequeo está copiado
  inline: `accounts/views.py:234` y `:245` repiten el mismo `raise PermissionDenied`,
  y `feed/views.py:12` y `restaurants/serializers.py:160-167` usan `friend_ids`
  directo.
- `visible_pins(viewer, owner=None, status=None)`: un único armado del queryset de
  Pin con su `select_related`/`prefetch_related` y **una sola semántica del filtro de
  status**. Hoy `pins/views.py:31` trata `status=all` como no-filtro y
  `accounts/views.py:254` no, así que un `?status=all` ahí devuelve vacío. Y
  `accounts/views.py:241` pone `pagination_class = None`: los pins de un amigo vienen
  completos y los propios paginados de a 20.

Sin estos dos módulos, los tres niveles de privacidad de la fase 2 se implementan
cinco veces.

### 0.4 — `pins/serializers_public.py`

Serializers públicos con lista de campos propia, sin heredar de los internos. Hoy
`SharedListPublicSerializer` (`pins/serializers.py:96-113`) reusa `PinSerializer` y
`RestaurantSerializer` tal cual, **así que cualquiera con un link compartido ya ve
`google_place_id`, `phone`, `address` y coordenadas exactas**. El único test
existente (`tests/pins/test_shared_list_public.py:41-56`) verifica sólo que no salga
el email.

Además: `get_pins` devuelve todos los pins del dueño sin tope ni paginación, y
`SharedListPublicView` (`pins/views.py:76-83`) no declara `throttle_scope`.

Shortlists, votación y QR agregan tres superficies anónimas más; heredar de los
serializers internos garantiza la fuga.

### 0.5 — `restaurants/filters.py`

django-filter ya está instalado y declarado como backend global (`settings.py:44`,
`:153-157`) pero está muerto en el viewset: `list` está sobrescrito
(`restaurants/views.py:67-74`) y llama `get_queryset_filtered()` sin pasar por
`filter_queryset()`. `nearby` (`:114-130`) usa `get_queryset()` pelado, o sea que
"cerca mío" no se puede combinar con ningún filtro.

- Un `RestaurantFilterSet` usado por `list` **y** por `nearby`.
- `ordering` en `Restaurant.Meta` (`models.py:85-87`), que hoy no lo tiene mientras
  el endpoint pagina → páginas inestables ya hoy.
- `nearby` filtra antes de recortar a `[:50]`, no después.

### 0.6 — Frontend: los seis módulos únicos

| Módulo | Reemplaza | Lo necesita |
|---|---|---|
| `api.getAll<T>()` + `page` en `pinsService.list()` | tres pantallas que leen sólo los primeros 20 pins | favoritos, colecciones, filtro |
| `PinCard.svelte` | 4 copias del markup de tarjeta | insider badge, favoritos, shortlists, colecciones |
| `TagChips.svelte` + `utils/taxonomy.ts` | `PersonaChips`, `TagCheckboxes`, `DietaryBadges`, `utils/dietary-badges.ts` | los 3 ejes, hashtags, filtro |
| `utils/share.ts` | el ternario de normalización de URL, dos veces en `profile/+page.svelte` | shortlists, QR |
| `services/google-import.ts` | el flujo details→fromGoogle, duplicado en `search` y `pin/new` (ya divergido en el manejo del 429) | importador |
| `createMap()` en `utils/map.ts` | 3 bootstraps de Leaflet con la URL de cartocdn pegada tres veces | mapa, LocationPicker |

Detalles que entran acá porque son gratis ahora y caros después:

- **`pinsService.list()` no acepta `page`** mientras `restaurants.service.ts:10` sí.
  El síntoma verificable: `map/+page.svelte:208-210` dibuja el mapa con 20 marcadores
  como máximo mientras `profile/+page.svelte:395-398` anuncia el `res.count` real.
- **Ninguna de las 5 `<img>` de foto de restaurante tiene `onerror`.** Cuando un
  photo ref de Google caduca, las cinco pantallas muestran el ícono roto. El fallback
  entra en `PinCard.svelte`.
- **`TagViewSet` (`restaurants/views.py:171`) necesita `?kind=`.** Hoy devuelve todo
  sin filtrar, y por eso `pin/new/+page.svelte:409-415` pinta `vegetarian`,
  `gluten-free` y `recommended` como opciones de "Vibe".

### 0.7 — Web pública

Stage de node en `nginx/Dockerfile.aws`, `location` explícitos en
`default-aws.conf`, `shared.html` borrado, y verificar que las rutas nuevas caigan
dentro del path filter de `.github/workflows/deploy.yml:6-12`.

---

## Fase 1 — beta

Orden por dependencia técnica. Cada bloque deja algo terminado.

### F1.1 — Caché de Google Places

Enganche en las dos únicas funciones que salen a Google por un id dado:
`google_places.details()` (`:110`) y `google_places.photo_uri()` (`:127`). Cachear
ahí cubre a todos los llamadores sin tocar un solo call site.

- **Details**: clave `(place_id, field_mask)` en Redis. Con el parser único ya hay un
  solo mask, pero la clave lo incluye igual para que un cambio de mask no sirva datos
  viejos.
- **Fotos**: bytes propios en S3, servidos por CloudFront, con `PlacePhoto(place_id,
  photo_ref, width, file, fetched_at, attribution)` y refresco a los 30 días. El
  contrato del endpoint no cambia: `Restaurant.image_url` sigue apuntando a
  `/api/v1/places/photo/`, que ahora redirige a CloudFront en vez de a Google.
  **Cero cambios de frontend.**
- `Cache-Control` en las respuestas de `places/views.py:410` y `:312-327`, que hoy no
  lo traen, así que ni el WebView de Capacitor ni nginx pueden reusar nada.
- **Eliminar el doble Place Details.** El frontend llama `details()` y después manda
  10 campos a `from_google`, que descarta todo menos `placeId` (`views.py:144`) y
  vuelve a pedirle lo mismo a Google (`google_import.py:66`). Con
  `google-import.ts` se manda sólo `{placeId}`; con la caché de details, la segunda
  llamada ni siquiera sale.
- **Atribución**: si servimos fotos cacheadas, hay que pedir `authorAttributions` —
  hoy no está en ningún field mask — y mostrarla. Es requisito de los términos.

### F1.2 — Analytics

App `analytics` nueva. **No reusar `feed.Activity`**: sus verbs son un set cerrado
(`feed/models.py:6-11`) y `Activity.pin` es CASCADE (`:19-25`), así que despinear
borraría el evento retroactivamente — exactamente lo contrario de lo que necesita una
evidencia de negociación.

- `Event(user FK SET_NULL null, name TextChoices, restaurant FK SET_NULL null,
  destination TextChoices, props JSONField, created_at)`.
  `name` como `TextChoices`, no CharField libre — regla del proyecto.
- Índices `(name, -created_at)` y `(restaurant, name, -created_at)` desde el día uno.
  El segundo es el que hace barato el reporte "clicks a OpenTable por venue por mes",
  que es literalmente el pedido de Jess.
- `save_to_map_count` se instrumenta **del lado servidor** (receiver en
  `pins/signals.py`, junto al que ya existe): un contador de negocio no se confía al
  cliente.
- `venue_card_view_count` con `IntersectionObserver` dentro de `PinCard.svelte` y
  dedupe por sesión.
- Endpoint `POST /api/v1/analytics/events/` con throttle scope propio.
- **`Event.user` no puede ser CASCADE**: `anonymise_user` tiene 35 tests críticos
  detrás y el invariante es "anonimiza conservando reseñas". Los eventos entran en
  ese contrato.
- **Revisión legal pendiente**: `docs/GDPR_PRIVACY_POLICY.md:97` declara "aggregate
  analytics" bajo interés legítimo. Un evento con user_id + venue + timestamp no es
  agregado, es comportamiento individual identificable. O se declara bien o los
  eventos van sin user_id.

**Dashboard**: template override de `admin/index.html` con los 4 números y la tabla
de `external_action_click` por venue/mes. Cero frontend, disponible el mismo día. La
alternativa —una pantalla en la app— obligaría a Jess a instalar el APK y
actualizarlo para ver su propio dashboard. Los agregados van en
`analytics/services/reports.py`, no inline en la view, y cacheados 5-15 minutos.

Nota: darle `is_staff` a Jess le da acceso a todo el admin, incluidos los emails de
todos los perfiles. Si eso no se quiere, hace falta un AdminSite restringido.

### F1.3 — Los tres ejes de tags

- Data migration: `Tag.Kind` += `vibe`/`occasion`/`scene`; reclasificar los 12 tags de
  `fixtures/tags.json` (hoy todos caen a `general` porque el fixture no declara
  `kind`, y ya mezclan los dos ejes: Quiet/Romantic/Trendy son Vibe, Outdoor-Terrace/
  Live Music/Pet Friendly son Scene); migrar las 12 Personas a `Tag(kind=occasion)`
  copiando `pins_pin_personas` a la M2M nueva.
- **Seedear por migración, no por fixture.** `make seed` no corre en prod: si los ejes
  se siembran por fixture, la prod queda con tres grupos vacíos.
- UI de 3 grupos en el step 2 de `pin/new` (hoy sólo tiene status, rating, notas y
  personas), espejada en `pin/[id]/edit`.
- **Distrito**: `restaurants/services/districts.py::district_for()` +
  `Restaurant.district` (CharField indexado). El dato ya viene en el payload de
  Google — los dos parsers lo tiran. Cero llamadas nuevas. Backfill por management
  command, no por migración, porque hay red de por medio.
- **Autoselección de vibe**: mapeos 1:1 contra tags que ya existen
  (`outdoorSeating`→outdoor-terrace, `liveMusic`→live-music,
  `allowsDogs`→pet-friendly). Función pura `inferred_tag_slugs(payload)` en el parser,
  testeada con payload mockeado. **Depende de verificar el SKU**: los atributos de
  atmósfera pueden estar en un tier más caro de Places. Se verifica contra el pricing
  antes de escribir una línea, y si sale caro se entrega sin autoselección.
- **Preselección por hora**: `suggestOccasion(date)` client-side, sin backend. Con dos
  salvaguardas: se marca visualmente como sugerencia y **no** se aplica a pins
  `to_visit` (guardar al mediodía un lugar al que querés ir no dice nada sobre la
  ocasión), y nunca en `pin/[id]/edit`, donde pisaría la elección del usuario.
- **i18n**: los nombres de tags salen crudos de la DB en inglés mientras la app tiene
  tres idiomas. Triplicar los ejes triplica el texto sin traducir. La traducción va en
  `taxonomy.ts` por slug.

### F1.4 — Favoritos

`Pin.is_favourite = BooleanField(default=False, db_index=True)`.

**No** un tercer `Pin.Status`: `unique_together (user, restaurant)` hace que marcar
favorito pisaría el pin existente, y `SharedList.status_filter` heredaría la opción.
**No** un modelo aparte: el producto ya obliga a pinear para opinar.

Glifo de estrella en componente propio — no reusar `HeartIcon.svelte`, que ya es el
rating.

Un detalle que es un bug visible y es gratis de evitar: `Pin.Meta.ordering =
["-updated_at"]` con `updated_at` en `auto_now` significa que togglear un favorito
reordena la lista bajo el dedo del usuario.

### F1.5 — Shortlist curada

`SharedListItem(shared_list, pin, position, note)` con `unique_together` y
`SharedList.kind` (`auto` | `curated`).

**`kind` default `auto`, obligatorio**: con default `curated`, todo link ya compartido
pasaría a mostrar cero restaurantes de golpe.

- Tope duro de 5-10 items validado en el serializer. "My top three" no necesita 200, y
  el tope elimina de raíz el problema de paginación del endpoint público.
- La página pública pasa a ser la ruta Svelte, servida en web (decisión 2).
- Caducidad: el link es un UUID sin expiración y `is_active` es el único apagador. Una
  shortlist llamada "Friday's girls lunch" tiene vida útil de días. Se agrega
  `expires_at` opcional.
- Verificar que el test crítico de borrado de cuenta siga pasando: `account_deletion.py:50`
  borra las SharedList y el CASCADE se lleva los items.

### F1.6 — Directions y reservas con tracking

Los botones **no existen**: 0 hits de `opentable|directions|maps.google|geo:|reserv`
en todo `app/src/`. La única salida externa hoy es el link al sitio del restaurante.
Esto importa porque `external_action_click` es el evento que justifica el bloque
entero y no hay nada que instrumentar hasta que los botones existan.

- Directions: cero backend. `utils/directions.ts` arma el deep link con lat/lng que ya
  vienen en el serializer.
- Reservas: `Restaurant.reservation_url` + `reservation_provider` (TextChoices),
  poblados a mano desde el admin. Google no expone reservas de forma confiable.
- **Riesgo a verificar en dispositivo, no en teoría**: abrir una URL externa desde el
  WebView de Capacitor. El único precedente en el código es un `<a target="_blank">` y
  no está verificado que abra el navegador del sistema en el APK. Los esquemas custom
  (`maps://`, `comgooglemaps://`) además requieren `LSApplicationQueriesSchemes` en el
  Info.plist de iOS.
- **Definir qué cuenta como "click" antes de medir.** Si Jess le va a mostrar el
  número a OpenTable, tiene que poder responder si es un tap o una navegación
  efectiva, si hay dedupe, y qué pasa con los bots.

### F1.7 — Verified Insider badge

`Profile.is_verified_insider = BooleanField(default=False, db_index=True)`, editable
en masa desde el admin.

La única forma de romper esto es silenciosa: olvidar `read_only_fields` en
`ProfileSerializer` y que cualquiera se auto-verifique con un PATCH. Test mínimo
obligatorio.

Va también en `UserAnonymousSafeSerializer` — en un link público es donde más valor
tiene.

---

## Fase 2 — full build

### F2.A — Tres niveles de privacidad

**Path crítico: mini-spec previa + TDD, por regla del proyecto.** Toca permisos.

- `Pin.visibility` nullable (NULL = heredar el default global) +
  `Profile.default_pin_visibility`. El default debe reproducir el comportamiento
  actual o cambia la visibilidad de todo lo ya guardado.
- Se implementa **dentro** de `visibility.py` y `selectors.py` (bloque 0), no vista
  por vista.
- **Son 9 puntos de acceso, no 2.** El que siempre se olvida es
  `restaurants/views.py:37-39`: `Avg("pins__rating")` y `Count("pins")` agregan sobre
  todos los pins, así que un pin privado seguiría contando en el promedio público del
  restaurante aunque las vistas de perfil estén bien.
- **Conflicto de producto a resolver antes de codear**: `get_reviews`
  (`restaurants/serializers.py:187-213`) muestra reseñas a no-amigos *a propósito*
  (decisión D-001). Los tres niveles chocan de frente con eso.

Va primero en la fase 2 porque es mucho más barato con la base casi vacía.

### F2.B — Reportar y bloquear

**No es una feature más: es requisito de publicación.** App Store Review Guideline
1.2 exige mecanismo de reporte y de bloqueo para apps con contenido generado por
usuarios, y Muse tiene reseñas públicas. Si el beta va a TestFlight con usuarios
reales, esto sube de prioridad.

- `Block(blocker, blocked)` direccional, con efecto simétrico en visibilidad.
- **El cambio clave: el bloqueo va dentro de `friendships.py`.** `are_friends`
  devuelve False si hay Block en cualquier dirección. Así feed, perfiles y stats
  heredan el filtro sin tocarse.
- La vista que se va a olvidar es `UserSearchView` (`accounts/views.py:114-128`), la
  única que no pasa por el service. Y `get_reviews`, que no filtra por `friend_ids`.
- `Report` con motivo (choices), detalle, status y admin para resolverlos.

### F2.C — Colecciones, hashtags y filtro multi-atributo

- `Collection` + `CollectionItem` + `Hashtag` con `get_or_create` al vuelo.
  Los hashtags libres son la **excepción consciente** a la regla del proyecto
  ("set finito → TextChoices o FK"): se documenta en el commit, con normalización
  (lowercase, slugify, strip del `#`, tope de largo y cantidad) para no terminar con
  `#DateNight`, `#datenight` y `#date-night` como tres cosas distintas.
- Filtro multi-atributo sobre el `RestaurantFilterSet` del bloque 0: AND entre ejes,
  OR dentro de cada eje. Con los tres ejes en la misma M2M distinguidos por
  `Tag.kind`, el AND requiere joins repetidos — hacerlo con un solo `tags__slug__in`
  da OR silencioso.
- UI: bottom sheet, no `<select>`. Cuatro ejes por N valores no entran en 390px.
- Sincronizar filtros con la query string.
- **Solapamiento a resolver en diseño**: colecciones, el eje Occasion y los hashtags
  permiten agrupar lo mismo de tres maneras. Sin una jerarquía clara, el usuario no
  sabe cuál usar.

### F2.D — Votación en shortlists

Primer endpoint de **escritura anónimo** del proyecto. Todo el modelo de amenazas
actual asume que escribir requiere JWT.

- `ShortlistVote(item, voter_key, voter_name, user null, created_at)`.
- Identidad sin cuenta: UUID en `localStorage`. No autentica nada — evita el doble
  voto accidental, no el fraude. Decirlo así, no venderlo como votación segura.
- `voter_name` es texto libre de un anónimo que se le muestra al dueño: escapado
  obligatorio, y **va después de F2.B** o sin nombre libre en v1. A un votante sin
  cuenta no lo podés bloquear; shortlist pública + nombre libre sin moderación es un
  canal de acoso sin remedio.
- Throttle propio, que recién es real con el Redis del bloque 0.

### F2.E — Push notifications

La más grande de las dos fases, y la única con dependencias fuera del repo: proyecto
Firebase y, para iOS, cuenta Apple Developer capaz de generar el APNs key.

Estado hoy: no hay `@capacitor/push-notifications`, no hay `google-services.json` ni
`GoogleService-Info.plist`, el manifest no declara `POST_NOTIFICATIONS`, y no hay
`.entitlements`. Lo único listo es el andamiaje de Gradle: `app/android/build.gradle:11`
ya trae el classpath de `google-services` y `app/android/app/build.gradle:71-78`
aplica el plugin condicionalmente si aparece el JSON.

- App `notifications`: `DeviceToken` + `services/dispatch.py::notify(user, kind,
  context)` como único punto de salida, unificando push y email.
- Refactor de `accounts/services/email.py` a `send_templated_email(template, lang,
  context)` genérico. Hoy es de propósito único con los subjects inline.
- **Cola obligatoria.** Notificar a N amigos dentro del `POST /api/v1/pins/` mete N
  round-trips a FCM en el camino crítico. El repo ya tiene el antecedente con Resend
  enviando inline dentro del request. Si se notifica desde signals, con
  `transaction.on_commit()`.
- Manejo de tokens muertos (FCM devuelve UNREGISTERED / INVALID_ARGUMENT), o la tabla
  se llena de basura y cada envío se hace más lento.
- Deep linking al tocar la notificación: hoy no hay ningún manejo de deep links.
- **Control de volumen**: `pins/signals.py:56-60` emite `Activity(UPDATED)` en cada
  edición con diff. Convertido en push, un usuario que corrige una reseña tres veces
  manda tres notificaciones a todos sus amigos.

### F2.F — QR de perfil

El QR es la parte fácil (`qrcode` + Pillow, que ya está). Lo caro es la superficie
pública de perfil, que hoy no existe.

- `Profile.public_slug` como token opaco. **Nunca el user_id numérico**: habilita
  enumeración trivial de toda la base de usuarios.
- Endpoint anónimo devolviendo el mínimo: display_name, avatar, city, badge.
- Choca con F2.A: hay que definir qué muestra el QR de un perfil privado.
- Escáner in-app = plugin de cámara nuevo = permiso nuevo en la review de la store.
  Evaluar si alcanza con abrir el link desde la cámara del sistema.

### F2.G — Importador

La pieza difícil ya está construida: `import_from_google_place_id`
(`google_import.py:123-186`) resuelve el find-or-create race-safe.

- `ImportJob(user, source, status, total, processed, matched, failed, report)`.
- CSV con la stdlib; Excel con `openpyxl`. Nada de pandas para 200 filas.
- **No puede ser síncrono**: 200 filas × 2 llamadas × 5s de timeout es un worst case
  de minutos dentro de un request. Necesita la cola de F2.E, o va después.
- **Problema de cuota verificado**: el scope `places` es 120/hour. Un CSV de 200 filas
  son ~400 llamadas facturables. Hace falta rate limiting propio del import y avisarle
  al usuario que va a tardar.
- **Pantalla de confirmación obligatoria**, no un lujo: el match por nombre acierta
  alto pero no perfecto, y un import ciego crea pins a restaurantes equivocados.
- `api.service.ts` sólo manda JSON (`'Content-Type': 'application/json'` hardcodeado
  en `:67`): subir un archivo necesita una variante multipart.

**Lo que hay que decirle a Jess que no se puede construir:**

| Fuente | Veredicto |
|---|---|
| CSV / Excel | Factible |
| Google Maps vía Takeout | Factible, UX mala (el usuario tiene que ir a Takeout y bajar un ZIP) |
| Google Maps vía API de lugares guardados | **No existe.** Google no publica ninguna API para leer las listas guardadas de un usuario |
| Apple Maps | **No factible.** No hay export de Guides ni API |
| Emails | **No factible con esfuerzo razonable.** OAuth de Gmail con scope restringido exige security assessment de terceros: miles de dólares y meses de trámite |
| SMS | **No factible.** No hay acceso programático al historial de mensajes en iOS |

---

## Escala a 100k usuarios

Lo que el bloque 0 y la fase 1 ya resuelven: Redis (caché y throttling real, hoy roto
por worker), S3 + CloudFront (fotos y avatares fuera del filesystem efímero), índices
en los campos que se filtran, paginación real en las tres pantallas que hoy leen 20
filas, y ordering estable en el endpoint paginado.

Lo que **no** se construye ahora y por qué: ALB + múltiples instancias + autoscaling
no lo pide ninguna feature, lo pide el volumen, y hoy no hay volumen. Lo que sí se
hace ahora es mantener el código **stateless** —nada en disco local, sesiones en JWT,
caché y colas fuera del proceso— de modo que pasar de una instancia a N sea un cambio
de infraestructura y no de código. Eso es exactamente lo que se le dijo a Jess: "es un
dial que giramos cuando los números lo pidan".

El cuello de botella real a esa escala no va a ser Django: va a ser el gasto de Google
Places si la caché no está bien hecha, y las queries agregadas del dashboard corriendo
en vivo sobre la tabla de eventos. Las dos están cubiertas arriba.

---

## Pendientes que no bloquean el arranque

- **Factura de Google Places.** Jess dijo que no tiene costos y que manda captura por
  WhatsApp. Define si la autoselección de vibe es viable (los atributos de atmósfera
  pueden estar en un SKU más caro). Sin ese dato, F1.3 se entrega sin autoselección.
- **Revisión legal de analytics.** La política actual declara "aggregate analytics";
  los eventos con user_id no son agregados.
- **Criterio escrito de Verified Insider** antes de tildar al primero.
- **Qué cuenta como "click"** para el número que va a ver OpenTable.
- **Números de escala en tramos** para el inversor: son estimaciones con rango, no
  cotizaciones, y van a terminar frente a un tercero.
