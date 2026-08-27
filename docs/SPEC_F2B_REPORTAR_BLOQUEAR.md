# Reportar y bloquear

**Estado: borrador v2, corregido tras revisión adversarial.** Toca permisos y visibilidad, así que por regla del
proyecto va mini-spec previa y TDD. Las cuatro decisiones de producto están
cerradas (ver Trazabilidad).

Base: discovery del 2026-08-27 sobre el código real, con el inventario de las
superficies que exponen datos de un usuario a otro verificado archivo por
archivo. Los cambios respecto de la v1 están al final, en "Qué cambió y por qué".

---

## 1 · Problema

Hoy no hay forma de sacarse a alguien de encima. Si una persona te incomoda,
podés rechazar su solicitud de amistad —y ni siquiera eso sirve de mucho: puede
borrar la fila y volver a solicitar sin tope— pero va a seguir encontrándote por
búsqueda con tu email, va a seguir viendo tus reseñas en cada restaurante, y vos
vas a seguir viendo las suyas. No existe ningún modelo, endpoint ni pantalla de
bloqueo, reporte o moderación: el grep sobre `backend/` y `app/src/` en los tres
idiomas no devuelve nada.

Con dos usuarios eso no se notó. El beta arranca la semana del **14 de
septiembre** con 12 a 30 personas que no se conocen entre sí, sobre un producto
cuyo contenido central son reseñas con nombre y foto.

Y hay una fecha dura por encima de la del beta: **App Store Review Guideline
1.2 exige mecanismo de reporte y de bloqueo para toda app con contenido
generado por usuarios.** Muse lo es. Sin esto, la app no se publica: no es una
feature más, es requisito de publicación.

## 2 · Usuarios y casos de uso

**Dos roles.** El usuario final de la app, y Gustavo como moderador desde el
admin de Django. No hay equipo de moderación ni rol intermedio.

| Rol | Caso | Qué hace |
|---|---|---|
| Usuario | Alguien me molesta | Lo bloquea: deja de verlo y de ser visto por él |
| Usuario | Me arrepentí | Lo desbloquea; la amistad **no** vuelve sola |
| Usuario | Vi contenido que no corresponde | Reporta la reseña, con motivo y detalle opcional |
| Usuario | Alguien se comporta mal en general | Reporta al usuario, no a un contenido puntual |
| Moderador | Llegó un reporte | Lo ve en el admin y por email; resuelve y deja constancia |

## 3 · Requisitos funcionales

### Bloquear

**RF1 — Bloquear, de forma idempotente.**
`POST /api/v1/auth/blocks/` con `{userId}`. La vista usa `get_or_create` dentro
de la transacción; el `unique_together` es la red, no el mecanismo.
*Aceptación:* se crea exactamente una fila `Block(blocker=yo, blocked=el otro)`,
y un **segundo POST con el mismo par responde 200 sin crear otra fila y sin
error de servidor**.

> `unique_together` por sí solo no da idempotencia: da `IntegrityError`, que sin
> manejar sale como 500. Es el mismo camino por el que pinear dos veces devolvía
> 500 en lugar de 409 (ver "Validación duplicada modelo+serializer" en el
> `CLAUDE.md`). El test tiene que hacer el segundo POST, no sólo mirar la tabla.

**RF2 — El bloqueo es silencioso.**
Al bloqueado no se le notifica ni se le muestra que fue bloqueado. La app no
tiene ninguna pantalla ni respuesta que diga "te bloquearon".
*Aceptación:* ningún endpoint devuelve el estado de bloqueo consultado por el
bloqueado; para él, quien lo bloqueó simplemente deja de aparecer, con el mismo
resultado que un usuario que no existe.

**RF3 — Bloquear rompe la amistad, y se lleva su rastro.**
Bloquear borra la `Friendship` en ambas direcciones **y las dos filas
`Activity(FRIENDSHIP)` que la anunciaron**, todo en la misma transacción.
*Aceptación:* con una `Friendship` ACCEPTED entre A y B, después de que A
bloquea a B no queda ninguna fila de `Friendship` entre ellos en ninguna
dirección, ni ninguna `Activity` de verbo `friendship` que los vincule. Y **un
tercero amigo de ambos deja de ver "A y B ahora son amigos" en su feed**.

> Sin esto, borrar la amistad deja huérfanas las dos filas que crea
> `accounts/signals.py:40,45`, porque no hay ningún signal de borrado — sólo
> `anonymise_user` las limpia explícitamente. El resultado sería un feed que
> le anuncia a terceros una amistad que ya no existe y que además tiene un
> bloqueo debajo. RF11 no alcanza: filtra por bloqueo con el viewer, y acá el
> viewer es un tercero sin bloqueo con ninguno de los dos.

**RF4 — Desbloquear no revive la amistad.**
*Aceptación:* tras bloquear y desbloquear, `are_friends(a, b)` es `False` y no
existe fila de `Friendship`; para volver a ser amigos hace falta una solicitud
nueva y su aceptación.

**RF5 — El bloqueado no puede volver a solicitar amistad.**
*Aceptación:* `POST /api/v1/auth/friendships/` de B hacia A, con A habiendo
bloqueado a B, responde 400 y no crea fila. El mensaje de error **no** dice que
hay un bloqueo (RF2): usa el mismo texto que cualquier otro rechazo de
solicitud.

**RF6 — Las solicitudes pendientes mueren con el bloqueo, y no reviven.**
Bloquear elimina la `Friendship` PENDING, y aceptar una solicitud comprueba el
bloqueo **en el momento de aceptar**, dentro de la misma transacción.
*Aceptación:* si existía una `Friendship` PENDING entre A y B, bloquear la
elimina y `GET /friendships/requests/` deja de devolverla para ambos. Y un
`PATCH` de aceptación que llega **después** del bloqueo responde 400 sin crear
amistad, aunque el cliente todavía tuviera la solicitud en pantalla.

> Es una carrera real, no teórica: A bloquea mientras B tiene la pantalla de
> solicitudes abierta y toca "aceptar". Sin el re-chequeo, el `PATCH` crea una
> `Friendship` ACCEPTED posterior al bloqueo y queda un bloqueo con una amistad
> viva debajo — el peor estado posible, porque `are_friends` diría `True`.

**RF7 — Desbloquear.**
`DELETE /api/v1/auth/blocks/{userId}/`.
*Aceptación:* borra la fila; a partir de ahí las superficies de RF9 a RF13
vuelven a comportarse como con un desconocido cualquiera — no como con un amigo.

**RF8 — Listar mis bloqueos.**
`GET /api/v1/auth/blocks/` devuelve a quiénes bloqueé, para poder desbloquear
desde la app.
*Aceptación:* devuelve sólo los bloqueos donde yo soy `blocker`; nunca aquellos
donde soy `blocked`, porque eso violaría RF2.

### Efecto del bloqueo en cada superficie

El efecto es **simétrico**: no importa quién bloqueó a quién, ninguno de los dos
ve al otro.

**RF9 — Perfil y pins del otro.**
*Aceptación:* `GET /auth/users/{id}/` y `GET /auth/users/{id}/pins/` devuelven
403 entre dos usuarios con bloqueo, aunque antes fueran amigos.

**RF10 — Búsqueda de usuarios.**
*Aceptación:* buscar por el email exacto, el teléfono exacto o el nombre de una
persona con la que hay bloqueo devuelve cero resultados, en las dos direcciones.

**RF11 — Feed.**
*Aceptación:* ninguna actividad cuyo `actor` esté bloqueado aparece en el feed,
y ninguna actividad expone en `target_user` a alguien con quien hay bloqueo.

> El segundo caso **ya es un bug hoy, sin bloqueo**: `feed/views.py:15` filtra
> por `actor` únicamente, así que la actividad de amistad de un amigo tuyo
> serializa el `target_user` con `UserPublicSerializer`, que incluye el email
> de una persona que no es amiga tuya. Se arregla acá.

**RF12 — Reseñas en la ficha del restaurante.**
Las reseñas de alguien con quien hay bloqueo no se muestran, en ninguna de las
dos direcciones. **Para cualquier tercero, esas reseñas siguen visibles.**
El filtro va **dentro de la query, antes del `[:20]`**, no sobre la lista ya
cortada.
*Aceptación:* con A y B bloqueados y ambos con reseña en el mismo restaurante,
A no ve la de B, B no ve la de A, y C —sin relación con ninguno— ve las dos. Y
en un restaurante con **más de 20 reseñas** donde las más recientes son del
bloqueado, quien bloqueó **sigue viendo 20 reseñas**, no menos.

> Dónde va el filtro no es un detalle de implementación. `get_reviews`
> (`restaurants/serializers.py:241`) corta con `[:20]` en SQL y recién después
> ordena en Python. Filtrar después del corte hace que alguien que bloqueó a un
> reseñador prolífico vea tres reseñas en un restaurante que tiene cincuenta —
> un agujero visible en la página principal del producto. La segunda mitad del
> criterio de aceptación existe para que ningún test pase con el filtro en el
> lugar equivocado.

> Esto **acota** D-001 sin derogarla: las reseñas siguen siendo públicas a
> no-amigos, que es la propuesta de valor. Lo único que cambia es que un
> bloqueo mutuo las oculta entre ese par. `docs/PRODUCT_DECISIONS.md` se
> actualiza en el mismo commit para que D-001 no siga diciendo "no filtres
> nunca acá".

**RF13 — Agregados de amigos.**
*Aceptación:* `friend_stats` de un restaurante no incluye los pins de alguien
bloqueado, ni cuenta su rating en el promedio de amigos.

**RF14 — El punto único de política, sin cambiar comportamiento.**
El bloqueo se implementa dentro de `accounts/services/visibility.py`, que gana
dos funciones:

- `blocked_user_ids(user)` — ids con los que hay bloqueo **en cualquier
  dirección**. Es el conjunto que usan todas las superficies; ninguna arma su
  propio `Q(blocker=…) | Q(blocked=…)`.
- `visible_friend_ids(viewer)` — `friend_ids(viewer) - blocked_user_ids(viewer)`.
  **Excluye al viewer, igual que `friend_ids`.** Es la que consumen `feed/views.py`
  y `restaurants/serializers.py`.

*Aceptación:* fuera de `accounts/services/` y de `tests/`, ningún módulo importa
`friend_ids` ni consulta el modelo `Block` directamente. Y —esto es lo que hay
que testear— **el feed sigue sin mostrar la actividad propia** y **la reseña
propia sigue sin marcarse `is_friend: true`**, exactamente como hoy.

> `visible_user_ids` **no** sirve acá, aunque el nombre lo sugiera: devuelve
> `friend_ids | {viewer.id}`, o sea que incluye al viewer. Migrar el feed a esa
> función haría que tu propia actividad empiece a aparecer en tu feed y que tu
> reseña se ordene entre las de tus amigos con `is_friend: true` — un cambio de
> producto colado dentro de un refactor. El repo ya advierte sobre esto en
> `visibility.py:47-52` y en un test `@critical`
> (`tests/pins/test_pin_selectors.py:96`): *"forgetting that is how a feed ends
> up hiding your own activity"*. `visible_user_ids` queda como está, para el
> filtrado de "datos que puedo ver" donde los propios sí cuentan.

**RF15 — Red de seguridad antes de tocar el feed.**
`GET /api/v1/feed/` **no tiene un solo test**: cero llamadas a la vista en toda
la suite. Antes de modificarlo (RF11 y RF14), se escriben tests de
caracterización que fijen el comportamiento actual.
*Aceptación:* existen tests que verifican, sobre el endpoint y no sobre los
services, que el feed muestra la actividad de los amigos, **no** muestra la
propia, y no muestra la de un desconocido. Se escriben **antes** del cambio y
pasan sin tocar código de producción.

### Reportar

**RF16 — Reportar a un usuario o una reseña, con copia de lo reportado.**
`POST /api/v1/auth/reports/` con `{reportedUserId, pinId?, reason, detail?}`.
`pinId` presente significa "reporto esta reseña"; ausente, "reporto a esta
persona". Cuando hay `pinId`, el reporte **guarda una copia del `comment` y el
`rating` tal como estaban al reportarlos**.
*Aceptación:* se crea una fila `Report` con `status=pending`; con `pinId` de un
pin que no pertenece al usuario reportado, responde 400. Y **si el autor edita
la reseña después de ser reportada, el moderador sigue viendo el texto original**
en el admin.

> Sin la copia, el reporte apunta a un `Pin` cuyo `comment` es editable: entre
> la denuncia y la revisión el autor cambia el texto por uno inocuo y el reporte
> se queda sin objeto. Es el movimiento obvio de alguien que escribió algo
> ofensivo, no un caso raro.

**RF17 — Motivos de un set cerrado.**
`reason` es `TextChoices`, no texto libre: acoso, spam, contenido inapropiado,
suplantación de identidad, otro.
*Aceptación:* un `reason` fuera del set responde 400. El `detail` libre es
opcional y tiene tope de largo.

**RF18 — El reporte llega a un humano.**
Cada reporte dispara un email al moderador por `accounts/services/email.py`, con
el motivo, el detalle y los ids necesarios para encontrarlo en el admin.
*Aceptación:* al crear un reporte se llama al envío una vez. **Si el envío
falla, el reporte igual se guarda y el usuario recibe la misma respuesta** —
perder la denuncia porque Resend está caído es peor que no avisar por mail.

**RF19 — Cola de moderación en el admin.**
`Report` tiene `status` (pendiente / revisado / accionado / descartado),
`resolved_at` y una nota de resolución, y se administra desde el admin de
Django, filtrable por status.
*Aceptación:* el admin lista los reportes pendientes primero y permite cambiar
el status dejando constancia de cuándo.

**RF20 — Reportar no revela nada al reportado.**
*Aceptación:* ningún endpoint le dice al reportado que fue reportado, ni quién
lo reportó.

**RF21 — Tope de reportes.**
Scope de throttle propio para la creación de reportes.
*Aceptación:* superado el tope, responde 429 y no crea fila.

### Ciclo de vida y datos

**RF22 — El borrado de cuenta se lleva los bloqueos y los reportes que emitió.**
`anonymise_user` borra las filas de `Block` en ambas direcciones y los `Report`
donde la persona es `reporter`.
*Aceptación:* tras anonimizar, no quedan filas de `Block` ni de `Report` como
emisor. **Los reportes *sobre* esa persona se conservan** con el usuario
desvinculado, igual que los eventos de analytics: son la constancia de una
denuncia que puede seguir abierta.

**RF23 — El bloqueo se refleja en la app.**
El perfil de otro usuario ofrece bloquear y reportar; Ajustes tiene la lista de
bloqueados con la opción de desbloquear; la ficha de una reseña permite
reportarla. **Al terminar de reportar, la app ofrece bloquear a esa persona en
el mismo paso** — es lo que quiere hacer casi siempre quien acaba de reportar
por acoso. Los tres idiomas.
*Aceptación:* el flujo se recorre desde la app con textos en es/en/it, y tras
enviar un reporte aparece la opción de bloquear sin volver a buscar a la
persona.

## 4 · Requisitos no funcionales

**Seguridad.** El bloqueo es una superficie de permisos: aplica la regla del
proyecto de filtrar siempre en `get_queryset` y de no confiar en que el cliente
oculte nada. Los endpoints nuevos son `IsAuthenticated`.

**Privacidad.** RF2 y RF20 son el requisito de fondo: ni el bloqueo ni el
reporte pueden ser observables por el destinatario, porque avisarle a un
acosador escala el conflicto en lugar de cortarlo.

**Rendimiento.** El conjunto de bloqueados se resuelve una vez por request y se
cachea igual que `friend_ids` hoy en `restaurants/serializers.py:209-214` —una
instancia de serializer por request, así que el caché ahorra exactamente una
query—. El bloqueo agrega una query por request en el peor caso.

Con **211 pins en producción**, cualquier análisis de costo es teórico hoy. Lo
que sí conviene anotar para cuando deje de serlo: `Activity` tiene
`Index(["actor", "-created_at"])`, y un `NOT IN` sobre `actor_id` no lo usa como
lo usa un `IN` — degrada a scan con filtro. Si el feed llega a doler, el camino
es `exclude` con subquery en vez de un set materializado en Python, no un índice
nuevo.

**i18n.** Motivos de reporte, textos de la UI y el email al moderador en los
tres idiomas.

**Observabilidad.** Cada bloqueo y cada reporte se loguean con los ids y el
resultado. Durante el beta, "me bloquearon y sigo viendo a la persona" tiene que
tener evidencia que mirar.

**Compliance.** Es el requisito que habilita la publicación (Guideline 1.2). El
criterio real de la revisión es que exista mecanismo de reporte **y** capacidad
de actuar sobre él: RF18 y RF19 son esa capacidad.

## 5 · Fuera de alcance

- **Filtrar el link público compartido.** `SharedListPublicView` es anónimo y
  sin `authentication_classes`: no hay viewer contra el cual evaluar un
  bloqueo. Quien tenga el link lo ve, bloqueado o no. Se acepta y **se declara
  en la UI de bloqueo**.

  Sobre revocarlo, con precisión: el backend lo permite —`SharedList` tiene
  `is_active` y `expires_at`, y el ViewSet acepta `PATCH` y `DELETE`— pero **la
  app hoy sólo expone borrar la lista** (`pins.service.ts` tiene
  `deleteSharedList` y no tiene ningún update; `isActive` está en el tipo y no
  se lee en ninguna pantalla). Así que la única revocación disponible para un
  usuario es destruir la lista entera. Se deja así en esta iteración; el texto
  de la UI de bloqueo dice eso y no promete un desactivar que no existe.
- **Suspender o expulsar cuentas.** El moderador puede hacerlo hoy desde el
  admin poniendo `is_active=False`; no se construye herramienta nueva.
- **Auto-ocultar contenido al llegar a N reportes.** Se evaluó; abre la puerta
  al abuso coordinado y con el volumen del beta no se justifica.
- **Notificar al reportante el desenlace de su reporte.** Requiere el sistema de
  notificaciones de F2.E.
- **Silenciar (mute) sin bloquear.** No está pedido.
- **Los tres niveles de privacidad (F2.A).** Se enchufan después en el punto
  único que esta spec deja armado.

## 6 · Edge cases

| Caso | Severidad | Manejo |
|---|---|---|
| Bloquear a alguien que ya bloqueé | Importante | Idempotente: no crea segunda fila, no rompe (RF1) |
| Bloqueo mutuo (A bloquea a B y B a A) | Importante | Dos filas, efecto igual: el filtro mira ambas direcciones |
| Bloquear a alguien que ya me bloqueó | **Crítico** | Se permite y no revela nada: si respondiera distinto, sería el oráculo que RF2 cierra |
| Bloquearse a uno mismo | Importante | 400. `are_friends(a, a)` devuelve `True` sin tocar la DB, así que un self-block rompería la visibilidad de los propios datos |
| Bloquear a un usuario anonimizado | Nice-to-have | Se permite; la fila queda y no molesta |
| La amistad se recreó por invitación | **Crítico** | `RegisterSerializer` crea `Friendship` ACCEPTED automáticamente al registrarse con un email invitado (D-005). Ese camino **tiene que respetar el bloqueo** o lo revive por la puerta de atrás |
| Reseña reportada cuyo autor se borra | Importante | El reporte sobrevive con el autor desvinculado (RF22) |
| Reportar un pin que no es del usuario reportado | Importante | 400 (RF16) |
| Reportar en masa a la misma persona | Importante | Throttle (RF21); el admin ve el volumen |
| Link compartido ya repartido | Importante | No se filtra; se declara y se ofrece revocarlo (§5) |
| Bloqueo entre dos personas con pins en el mismo restaurante | Importante | Cada uno ve la ficha sin el otro; el promedio global del restaurante no cambia |
| Feed con actividad vieja del bloqueado | Importante | Se filtra al leer, no se borra: el bloqueo es reversible |
| Actividad de amistad huérfana tras el bloqueo | **Crítico** | Se borra junto con la `Friendship` (RF3): filtrarla no alcanza, porque para un tercero sin bloqueo seguiría visible |
| Aceptar una solicitud justo después de ser bloqueado | **Crítico** | Re-chequeo del bloqueo al aceptar, en transacción (RF6) |
| La reseña reportada se edita antes de la revisión | **Crítico** | El reporte guarda copia del comentario y el rating (RF16) |
| Restaurante con más de 20 reseñas del bloqueado | Importante | El filtro va en la query, antes del corte (RF12) |
| `friend_count` del perfil baja al bloquear | Nice-to-have | Se acepta: como el bloqueo borra la amistad (RF3), el contador baja para todos. Es una señal débil y el costo de ocultarla —un conteo distinto por espectador— no lo justifica |
| El cliente tiene el feed cacheado con el bloqueado adentro | Importante | La app refresca el feed al volver de bloquear; el backend ya filtra en la siguiente request |

## 7 · Riesgos

| Riesgo | Prob. | Impacto | Mitigación |
|---|---|---|---|
| Se olvida una superficie y el bloqueo es cosmético | **Alta** | Alto | Son 5 puntos que no heredan de ningún service. RF10 a RF13 los nombran uno por uno y RF14 los concentra para que el próximo no se olvide |
| Cambiar el feed lo rompe sin que nadie se entere | **Alta** | Alto | **`GET /api/v1/feed/` no tiene un solo test**: cero llamadas a la vista en toda la suite, verificado. RF15 exige tests de caracterización escritos y en verde **antes** de tocarlo |
| Migrar a la función equivocada cambia el producto | Media | Alto | `visible_user_ids` incluye al viewer y `friend_ids` no. RF14 fija `visible_friend_ids` y pone el comportamiento actual como criterio de aceptación |
| 23 RF no entran antes del 14/9 | **Alta** | Alto | El orden de implementación es: modelo + service + las 5 superficies (lo que exige la guideline), y recién después la UI de reportes. Si algo se cae, se cae por el final. **Los reportes sin UI de moderación propia siguen cumpliendo: el admin de Django alcanza** |
| El revisor de App Store considera insuficiente el mecanismo | Baja | Alto | RF18 + RF19 dan reporte **y** capacidad de actuar, que es el criterio |
| D-005 revive una amistad bloqueada | Media | Alto | Está como edge case crítico y va con test |
| Llegar tarde al 14/9 | Media | Alto | El alcance está acotado: sin auto-moderación, sin notificaciones, sin mute |

## 8 · Stack propuesto

Sin dependencias nuevas.

**Modelos en `accounts`.** `Block(blocker, blocked, created_at)` con
`unique_together` para hacer la idempotencia de RF1 un invariante de base y no
una comprobación en Python. `Report(reporter, reported_user, pin, reason,
detail, status, resolved_at, resolution_note)`.

Se descartó reusar `Friendship.DECLINED` como bloqueo: hoy no filtra nada, la
fila la puede borrar el emisor y volver a solicitar, y mezclaría dos conceptos
en una tabla cuyo `unique_together` es direccional.

**La política vive en `accounts/services/visibility.py`.** Ese módulo ya tiene
`can_view` y `visible_user_ids` escritas y testeadas, **sin un solo llamador en
producción**: existen exactamente para esto. `friendships.py` sigue respondiendo
el hecho ("¿son amigos?") y `visibility.py` la política ("¿puede ver esto?").

Se descartó meter el bloqueo dentro de `are_friends`, que es lo que propone
`docs/PLAN_FASES.md:361-363`. Dos razones. La primera es de diseño: `are_friends`
pasaría a devolver `False` para dos personas que en la base son amigas, o sea a
mentir sobre el hecho que nombra, rompiendo la separación que el propio
`CLAUDE.md` documenta. La segunda es que el argumento a favor no se sostiene
contra el código: el plan dice que así "feed, perfiles y stats heredan el filtro
sin tocarse", pero `are_friends` no lo llama ninguna vista —vive como alias en
`accounts/views.py:89` para los tests— y `friend_ids` tiene sólo dos llamadores.
Heredan tres superficies; se escapan cinco, no dos.

**Email al moderador por el service existente**, con
`send_report_notification_email` al lado de los otros dos. Es regla del
proyecto: los emails del producto no pasan por `django.core.mail`.

**Frontend:** pantalla de perfil de usuario para bloquear/reportar, sección en
Ajustes para la lista de bloqueados, y acción de reportar en la reseña. Claves
i18n nuevas en los tres idiomas.

## 9 · Trazabilidad

| RF / decisión | Origen |
|---|---|
| Problema, requisito de publicación | `docs/PLAN_FASES.md:353-358` + decisión de Gustavo de priorizarlo |
| RF1, RF7, RF8 — endpoints de bloqueo | Consecuencia de la decisión de construir bloqueo |
| RF2 — silencioso | Respuesta de Gustavo: "silencioso, y rompe la amistad" |
| RF3, RF4 — rompe la amistad, no revive | Respuesta de Gustavo, misma decisión |
| RF5, RF6 — no puede re-solicitar | Verificado: hoy el emisor borra la fila DECLINED y re-solicita sin tope |
| RF9 — perfil y pins | Verificado: `require_can_view` en `accounts/views.py:279,289` |
| RF10 — búsqueda | Verificado: `accounts/views.py:159-173` no filtra por relación y expone email |
| RF11 — feed | Verificado: `feed/views.py:15` filtra sólo `actor`; `target_user` se serializa con email |
| RF12 — reseñas | Respuesta de Gustavo: ocultarlas sólo para el par, D-001 intacta para terceros |
| RF13 — friend_stats | Verificado: `restaurants/serializers.py:225` |
| RF14 — punto único | Verificado: `can_view` y `visible_user_ids` no tienen llamadores en producción |
| RF16, RF17 — reportar con motivos cerrados | Respuesta de Gustavo (opción con `pin?`) + regla del proyecto sobre sets finitos |
| RF18, RF19 — email + cola en el admin | Respuesta de Gustavo: "cola en el admin + email a vos" |
| RF20 — no revela al reportado | `[ASSUMPTION]` — no se preguntó; es la contraparte de RF2 y sin esto reportar se vuelve un ataque |
| RF21 — throttle | `[ASSUMPTION]` — patrón del proyecto: todo endpoint sensible lleva scope |
| RF22 — borrado de cuenta | Verificado: `anonymise_user` enumera qué destruye; el precedente de analytics define qué se conserva |
| RF23 — UI trilingüe | Verificado: la app ya es trilingüe |
| Modelo propio, no `Friendship.DECLINED` | Verificado: `DECLINED` no filtra nada y la fila es borrable por el emisor |
| Orden F2.B antes que F2.A | Respuesta de Gustavo |
| RF1 idempotente con `get_or_create` | Critique: `unique_together` da `IntegrityError`, no idempotencia |
| RF3 borra las `Activity` de amistad | Critique + verificado: no hay signal de borrado, sólo `anonymise_user` las limpia |
| RF6 re-chequeo al aceptar | Critique (carrera bloquear/aceptar) |
| RF12 filtro antes del `[:20]` | Critique + verificado: `restaurants/serializers.py:241` corta en SQL |
| RF14 `visible_friend_ids`, no `visible_user_ids` | Critique + verificado: `visibility.py:47-52` y `tests/pins/test_pin_selectors.py:96` |
| RF15 tests de caracterización del feed | Verificado: cero tests tocan `FeedView` en toda la suite |
| RF16 copia del contenido reportado | Critique (la reseña se edita entre el reporte y la revisión) |
| RF23 ofrecer bloquear tras reportar | Critique (los dos flujos estaban desconectados) |
| Revocación del link: sólo borrar | Verificado: el frontend no expone `PATCH`, sólo `deleteSharedList` |
| D-005 revive amistades | Verificado: `accounts/serializers.py:141-155` |

**Dos items `[ASSUMPTION]` sobre treinta: 6,7%.**

## Sugerencias fuera de scope

- **Un tope de re-solicitudes de amistad**, con bloqueo o sin él. Hoy alguien
  puede solicitar, ser rechazado, borrar la fila y volver a solicitar
  indefinidamente. El bloqueo lo corta sólo si la víctima lo usa.
- **El oráculo de enumeración de `EmailInvitationSerializer`**
  (`accounts/serializers.py:243-246`), que confirma si un email tiene cuenta en
  Muse. Es el mismo agujero que quedó abierto en el reset de contraseña.


## 10 · Qué cambió y por qué

| v1 | v2 | Motivo |
|---|---|---|
| RF14 migraba feed y reviews a `visible_user_ids` | Migran a `visible_friend_ids`, con el comportamiento actual como criterio | `visible_user_ids` incluye al viewer: el feed habría empezado a mostrar tu propia actividad y tu reseña se habría marcado `is_friend`. Un cambio de producto escondido en un refactor, contra el que el repo ya advierte en un test `@critical` |
| RF1 se apoyaba en `unique_together` para ser idempotente | `get_or_create` en transacción, con el segundo POST como criterio | `unique_together` da `IntegrityError` → 500. Es el mismo camino del pin duplicado que ya devolvió 500 en vez de 409 |
| RF12 no decía dónde iba el filtro | Va en la query, antes del `[:20]`, y el criterio lo verifica con más de 20 reseñas | Filtrar después del corte deja al que bloqueó viendo tres reseñas en un restaurante que tiene cincuenta |
| El conjunto bidireccional no estaba nombrado | `blocked_user_ids(user)` en `visibility.py` | Sin una función única, cada una de las cinco superficies arma su propio `Q` bidireccional y se reproduce el problema que la spec dice resolver |
| Nada sobre las `Activity` de amistad | RF3 las borra en la misma transacción | Borrar la `Friendship` dejaba dos filas huérfanas anunciando a terceros una amistad que ya no existe |
| Nada sobre aceptar una solicitud ya bloqueada | RF6 re-chequea al aceptar | La carrera dejaba un bloqueo con una amistad ACCEPTED viva debajo |
| El reporte apuntaba a un `Pin` editable | RF16 guarda copia del comentario y el rating | El autor edita el texto y el reporte se queda sin objeto |
| Reportar y bloquear eran flujos separados | RF23 ofrece bloquear al terminar de reportar | Es lo que quiere hacer casi siempre quien reporta por acoso |
| "el dueño ya puede revocar el link" | Puede borrar la lista; desactivar no está en la app | El frontend no expone `PATCH`: `isActive` existe en el tipo y no se lee en ninguna pantalla |
| Sin red antes de tocar el feed | RF15: tests de caracterización primero | `GET /api/v1/feed/` no tiene un solo test en toda la suite |
