# Decisiones de producto — muse

> Decisiones de comportamiento del producto que están implícitas en el
> código pero merecen documentación explícita. Si dudás de una de estas
> decisiones, leé el contexto antes de "arreglar" el código.

---

## D-001: Reviews son públicas

**Contexto**: cuando un usuario pide la página de un restaurant, ve los
últimos 20 pins con comentario, ordenados por amigos primero. Pero la lista
NO se filtra por amistad — incluye reviews de usuarios desconocidos.

**Decisión**: público por diseño. Los pins son la propuesta de valor de
Muse: "ver lo que opina la gente sobre este restaurant", no solo amigos.

**Materializa en**: `backend/restaurants/serializers.py:RestaurantDetailSerializer.get_reviews`.

**No hagas**: filtrar por `_are_friends(reviewer, request.user)` ahí.
Romperías la propuesta de valor.

---

## D-002: from_google auto-aprueba el Restaurant

**Contexto**: cuando un usuario importa un restaurant desde Google Places,
el Restaurant se crea con `approval_status='approved'` directamente (no
pasa por workflow pending → approved).

**Decisión**: la fuente Google es confiable, los duplicados se manejan por
`google_place_id` único, los datos vienen consistentes. Pasarlo por
approval workflow agregaría fricción sin valor.

**Materializa en**: `backend/restaurants/views.py:RestaurantViewSet.from_google`.

**No hagas**: cambiar `approval_status='pending'` ahí. Si surge necesidad
de moderación de imports de Google, pensar mecanismo distinto (flagging
post-creation, no workflow upfront).

---

## D-003: El feed se mantiene consistente vía Django signals

**Contexto**: el modelo `Activity` en `feed/` no se escribe directo desde
las views. Se escribe desde signals de `pin/post_save`,
`accounts/Friendship.post_save`, `accounts/User.post_save`.

**Decisión**: la consistencia del feed depende de que cada acción de
usuario dispare la signal correcta. Si una nueva acción debería aparecer
en el feed, hay que crear la signal, no escribir Activity desde la view.

**Materializa en**: `backend/pins/signals.py`, `backend/accounts/signals.py`.

**No hagas**: escribir Activity directamente desde una view. Romperías el
invariante "cada Activity tiene una signal correspondiente".

---

## D-004: JWT con refresh lock contra paralelos

**Contexto**: el frontend en `lib/services/api.service.ts` tiene un lock
(`refreshPromise` singleton, `api.service.ts:22-23`) que impide que dos
requests al endpoint `/auth/token/refresh/` corran en paralelo cuando
expira el access token. Si N requests ven el 401 al mismo tiempo, una sola
hace refresh, las otras esperan al mismo `refreshPromise`.

**Decisión**: SimpleJWT está configurado con `ROTATE_REFRESH_TOKENS=True`
(ver `settings.py:SIMPLE_JWT`), que invalida el refresh token en cada uso.
Sin el lock, N requests intentando refresh paralelos producen N-1 fallos
con 401 permanente y deslogean al usuario.

**Materializa en**: `app/src/lib/services/api.service.ts` — variable
`refreshPromise` y la función `refreshAccessToken`.

**No hagas**: simplificar la lógica del lock pensando "es overhead". Sin
él, los usuarios se desloguean cuando se les vence el token y tienen
varios fetches activos.

---

## D-005: Auto-friendship por invitación es ACCEPTED, no PENDING

**Contexto**: cuando un usuario A invita por email a B y B se registra
usando el link de invitación, se crea automáticamente una Friendship entre
ellos.

**Decisión**: la friendship se crea con `status=ACCEPTED`. Razón: el email
de invitación promete "la amistad se creará automáticamente" — el contrato
del producto es que aceptar la invitación = aceptar la amistad. Pedir un
segundo paso de "aceptar amistad" después del registro es fricción
innecesaria y contradice el mensaje del email.

**Estado actual**: BUG conocido — el código hoy crea con `status=PENDING`
(ver `AUDIT_BUGS_FOUND.md` #1). El test 2 de A-001
(`test_register_creates_profile_and_consumes_invitation`) documenta el
comportamiento actual para mantener verde la suite. La fix es trivial
(1 línea) y va a ejecutarse en C-008 cuando lleguemos a Fase C.

**Materializa en**: `backend/accounts/serializers.py:83` (ahí vive el bug
a fixear).

**No hagas**: pensar que PENDING es la intención del producto y "fixear"
el test 2 invirtiéndolo SIN cambiar el código. La intención del producto
es ACCEPTED.

---

## D-006: User search requiere 3+ caracteres

**Contexto**: `UserSearchView` retorna lista vacía si la query tiene menos
de 3 caracteres. El comentario en código dice "to reduce mass enumeration
by short prefixes".

**Decisión**: anti-enumeration. Sin el mínimo, un atacante con la cuenta
"a" haría requests con queries `"a"`, `"b"`, `"c"`, … y mapearía progresivamente
todo el directorio de usuarios. Con 3 chars + throttle por scope (`user_search`,
60/hour) la enumeración masiva queda costosa.

**Materializa en**: `backend/accounts/views.py:UserSearchView.get_queryset`
(check `len(query) < 3`) y el throttle `user_search` en `settings.py`.

**No hagas**: bajar el mínimo a 1 o 2 chars "para mejorar UX al tipear",
ni quitar el throttle pensando que es ruido. Cualquier ajuste acá tiene
que considerar enumeración.

---

[Agregar más decisiones aquí cuando aparezcan]
