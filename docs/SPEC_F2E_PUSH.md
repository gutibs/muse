# Push notifications

**Estado: borrador v1.** Estrena infraestructura (una cola) y toca el envío de
mensajes a terceros, así que va mini-spec previa por regla del proyecto. Las
cuatro decisiones de producto están cerradas (ver Trazabilidad).

Base: discovery del 2026-09-06 sobre el código real. El proyecto Firebase ya
existe (`muse-d8986`, ver `reference_firebase` en las notas) y el
`google-services.json` está en el repo con el plugin de Gradle aplicándose.

---

## 1 · Problema

Muse no tiene forma de traer a nadie de vuelta. La app se abre cuando la
persona se acuerda sola, y los números dicen que no se acuerda: al 2 de
septiembre, en producción había **210 pins, 0 tags, 0 favoritos, 0 listas
curadas y 1 link de reserva**, con tags, favoritos y listas publicados desde el
21 de agosto. Se construyeron features que nadie volvió a mirar.

Todo lo que pasa en Muse le pasa a una persona sin que se entere. Alguien te
manda una solicitud de amistad y la vas a ver la próxima vez que abras la app,
que puede ser nunca. Un amigo califica el lugar al que ibas a ir el sábado y no
te enterás. El feed existe, pero un feed sólo funciona si alguien entra a
mirarlo.

Es el único bloque de la fase 2 que ataca ese problema: los demás (colecciones,
votación, QR) agregan superficie a un producto cuya superficie actual no se
usa.

## 2 · Usuarios y casos de uso

**Un solo rol**: la persona que usa Muse. No hay rol de administrador acá — el
admin de Django no manda notificaciones y no se le agrega esa capacidad (ver
Fuera de alcance).

| Caso | Quién dispara | Quién recibe |
|---|---|---|
| Recibo una solicitud de amistad | quien la manda | el destinatario, uno |
| Me aceptan una solicitud | quien acepta | quien la había mandado, uno |
| Un amigo pinea o califica un lugar | el amigo | todos sus amigos, N |
| Apago las que no quiero | la propia persona | — |

## 3 · Requisitos funcionales

### Registro del dispositivo

**RF1** — La app registra su token de FCM contra `POST /api/v1/notifications/devices/`
al iniciar sesión y cada vez que FCM lo rota. El endpoint es idempotente: el
mismo token para el mismo usuario no crea una segunda fila.
*Criterio*: dos POST idénticos dejan una sola fila; el segundo devuelve 200.

**RF2** — Un token que ya existía asociado a otro usuario cambia de dueño en
lugar de duplicarse. Pasa de verdad: dos cuentas en el mismo teléfono.
*Criterio*: registrar con el usuario B un token que tenía A deja una fila, con
`user = B`. A deja de recibir.

**RF3** — Cerrar sesión borra el token de ese dispositivo.
*Criterio*: después del logout, el token no está en la tabla y un envío a ese
usuario no lo incluye.

**RF4** — Borrar la cuenta borra sus tokens. Entra en el contrato de
`anonymise_user` (D-009), que hoy tiene tests críticos: el badge de Insider ya
está ahí porque es identidad, y un token de dispositivo lo es más.
*Criterio*: test crítico junto a los de borrado; después de anonimizar, cero
tokens de ese usuario.

### Preferencias

**RF5** — Cada persona tiene tres preferencias independientes: solicitud de
amistad recibida, solicitud aceptada, actividad de un amigo. Se leen y escriben
por el perfil.
*Criterio*: el serializer las expone y un PATCH las cambia.

**RF6** — Las tres arrancan **encendidas**, incluidas las de los usuarios que
ya existen.
*Criterio*: un usuario nuevo tiene las tres en `true`; la migración deja en
`true` a los 15 actuales.

**RF7** — Una preferencia apagada corta el envío en el punto único, no en la
vista. Apagar "actividad de un amigo" no puede dejar de notificar una solicitud
de amistad.
*Criterio*: con una apagada y las otras dos encendidas, sólo se encola lo que
corresponde.

### Qué notifica y qué no

**RF8** — Se notifican exactamente tres cosas: `friendship_request`,
`friendship_accepted` y `friend_activity` (un amigo pineó o calificó).
*Criterio*: la lista de tipos es cerrada y está en un `TextChoices`.

**RF9** — **Las ediciones no notifican nunca.** `Activity.Verb.UPDATED` existe
y seguirá alimentando el feed, pero no genera push. Corregir una reseña tres
veces manda cero notificaciones.
*Criterio*: test dedicado — editar un pin tres veces deja el feed con tres
entradas y la cola vacía.

**RF10** — Un pin que no es visible para el destinatario no genera
notificación. La política de visibilidad de F2.A manda también acá: notificar
"tu amigo pineó un lugar" sobre un pin privado lo delata igual que mostrarlo.
*Criterio*: test crítico — pin con `visibility=private` u `only_friends` con un
no-amigo: cero notificaciones. Se resuelve reusando `visible_pin_filter`, no
con una condición nueva al lado.

**RF11** — Un bloqueo corta la notificación en las dos direcciones, porque
`are_friends` ya devuelve False si hay `Block` (F2.B).
*Criterio*: test — con bloqueo activo, la actividad de uno no encola nada para
el otro.

### La cola

**RF12** — Ningún envío a FCM ocurre dentro de un request HTTP. El signal
escribe filas en `NotificationJob` con `transaction.on_commit()`; un comando
las despacha después.
*Criterio*: test que cuenta queries/llamadas — un `POST /api/v1/pins/` con 20
amigos no hace ninguna llamada HTTP saliente.

**RF13** — El despachador es idempotente y seguro ante corridas solapadas: toma
los trabajos con `select_for_update(skip_locked=True)`.
*Criterio*: dos despachadores en paralelo sobre la misma cola no mandan dos
veces el mismo job.

**RF14** — Un job que falla se reintenta con backoff hasta 3 veces y después
queda `failed` con el error guardado. Un fallo de un destinatario no aborta el
lote.
*Criterio*: con FCM devolviendo 500 para un token y 200 para otro, el segundo
se entrega y el primero queda para reintento.

**RF15** — Los tokens que FCM rechaza como `UNREGISTERED` o `INVALID_ARGUMENT`
se borran. Sin esto la tabla se llena de basura y cada envío se hace más lento.
*Criterio*: con esa respuesta mockeada, la fila del token desaparece y el job
no se reintenta.

**RF16** — Los jobs entregados se borran después de 7 días, desde el mismo cron
de mantenimiento que ya limpia el resto.
*Criterio*: comando `prune_notification_jobs` con test de corte por fecha.

### Idioma

**RF17** — `Profile.language` persiste el idioma elegido y es la fuente para el
texto de la notificación. Hoy el idioma sólo viaja en el request
(`request.data.get("language")`), y el push lo inicia el servidor: no hay
request del destinatario de donde sacarlo.
*Criterio*: con dos usuarios en idiomas distintos, el mismo evento produce dos
textos distintos.

**RF18** — El texto sale de `gettext` con `translation.override(...)`, el mismo
mecanismo que se puso el 2026-09-06 para los errores de la API, y los catálogos
`es`/`it` cubren los tres tipos.
*Criterio*: el test guardián de i18n sigue en verde y los mensajes nuevos están
en los `.po`.

### La app

**RF19** — La app pide el permiso de notificaciones **después** de que la
persona hizo algo en Muse, no en el primer arranque. Android 13+ exige
`POST_NOTIFICATIONS` y un permiso negado no se vuelve a pedir.
*Criterio*: no se pide en el onboarding; se pide al mandar o aceptar la primera
solicitud de amistad.

**RF20** — Tocar una notificación abre la pantalla correspondiente: el perfil
de quien te solicitó, o la ficha del restaurante. Hoy no hay ningún manejo de
deep links.
*Criterio*: con la app cerrada y con la app en background, el tap lleva a la
ruta correcta.

## 4 · Requisitos no funcionales

- **Privacidad (GDPR/PDPO)**: el token de dispositivo es dato personal y Google
  entra como procesador. Hay que declararlo en `nginx/landing/privacy.html` en
  los tres idiomas **en el mismo release**, no después. El cuerpo de la
  notificación no lleva contenido sensible: dice quién y qué lugar, nunca el
  texto de una reseña privada.
- **Seguridad**: la service account key de FCM va por variable de entorno y no
  al repo. El allowlist de `gitleaks` cubre sólo `google-services.json` y no se
  amplía para esto.
- **Observabilidad**: cada envío deja una línea con tipo, destinatario y
  resultado. `LOGGING` ya existe desde el 2026-09-02.
- **i18n**: tres idiomas, sin excepción — ver RF17 y RF18.
- **Performance**: el objetivo es que el `POST /pins/` no cambie su tiempo de
  respuesta. Latencia de entrega aceptada: hasta 2 minutos.

## 5 · Fuera de alcance

- **iOS.** El APNs key exige cuenta Apple Developer y eso está bloqueado por el
  trámite de titularidad con Jess. El diseño no se cierra contra iOS: `notify()`
  no asume FCM en su firma.
- **Migrar los emails existentes a la cola.** `notify()` nace como punto único
  pero hoy despacha sólo push. Invitación, reset y bienvenida se quedan como
  están: no se toca el path de auth en el mismo cambio que estrena una cola.
- **Notificaciones de marketing o novedades del producto.** Sólo los tres tipos
  de RF8.
- **Agrupación de notificaciones** ("3 amigos pinearon hoy"). Con 15 usuarios no
  hay volumen que lo justifique; se reevalúa si aparece.
- **Notificaciones en web.** La app no se sirve por web más allá de
  `/shared/<token>`.
- **Un panel para mandar notificaciones a mano desde el admin.** Es la puerta
  para el spam y no lo pidió nadie.

## 6 · Edge cases

| Caso | Severidad | Manejo |
|---|---|---|
| Pin privado o de sólo-amigos | **crítico** | RF10, con `visible_pin_filter`. Notificar delata igual que mostrar |
| Dos cuentas en el mismo teléfono | importante | RF2: el token cambia de dueño |
| El token murió (app desinstalada) | importante | RF15: se borra ante UNREGISTERED |
| El despachador tarda más de un minuto y se solapa con el siguiente | importante | RF13: `skip_locked` |
| La persona nunca aceptó el permiso de Android | importante | No hay token, no hay job. La preferencia queda encendida pero no llega nada; la pantalla de ajustes tiene que decirlo |
| Un amigo pinea 20 lugares seguidos | importante | Sin agrupación por decisión explícita. Se mira si molesta |
| FCM caído | importante | RF14: reintento con backoff; los jobs quedan en la tabla |
| Bloqueo mutuo | crítico | RF11, heredado de `are_friends` |
| Cuenta borrada entre el encolado y el envío | nice-to-have | El despachador vuelve a mirar preferencias y tokens al despachar, no al encolar |

## 7 · Riesgos

| Riesgo | Prob. | Impacto | Mitigación |
|---|---|---|---|
| El cron por minuto con `docker-compose exec` pesa en un t3.small | media | medio | Un solo comando que procesa el lote entero, no uno por job. Medir antes de bajar la frecuencia |
| Cambiar la naturaleza del cron de mantenimiento (semanal) a uno operativo (por minuto) | media | bajo | Archivo separado o sección aparte con comentario; el deploy ya lo instala |
| El permiso de Android se pide mal y la persona lo niega para siempre | media | alto | RF19: pedirlo en contexto. Un `no` de Android 13+ no se vuelve a preguntar |
| La política de privacidad queda sin actualizar | media | alto | Entra en la definición de terminado del bloque, no en un TODO |
| Notificar delata un pin privado | baja | **muy alto** | RF10 con test crítico. Es el oráculo que F2.A cerró, reabierto por otra puerta |
| `Profile.language` nace vacío para los 15 usuarios actuales | alta | bajo | La migración usa `en`, que es el default de la app; la app lo actualiza al abrir |

## 8 · Stack propuesto

- **FCM HTTP v1** con una service account. No hay alternativa en Android: es el
  único transporte que el sistema operativo acepta.
- **Cola: tabla `NotificationJob` en Postgres + management command
  `dispatch_notifications` desde el cron existente.** Descartado Redis: el
  desplegado corre con `--save ""` y `--maxmemory-policy allkeys-lru`, así que
  pierde trabajos en un restart y puede perderlos por desalojo; sirve como
  caché, que es para lo que se eligió. Descartado Celery: broker, worker y
  configuración para lo que hoy son decenas de notificaciones por día.
  Descartado un segundo Redis con RQ: otro contenedor y otro proceso en un
  t3.small de 2 GB que ya corre nginx, gunicorn con 3 workers y el Redis de
  caché.
- **App `notifications` en Django**, con `services/dispatch.py::notify(user,
  kind, context)` como único punto de salida, siguiendo el patrón de los
  services canónicos del proyecto.
- **`@capacitor/push-notifications`** en el frontend. El andamiaje de Gradle ya
  está.
- Sin dependencias nuevas de Python más allá del cliente de Google para firmar
  el token de la service account.

## 9 · Trazabilidad

| RF / decisión | Origen |
|---|---|
| RF1–RF4 (registro de dispositivo) | Necesario para cualquier push; patrón estándar de FCM |
| RF5, RF7 (preferencias por tipo) | **Respuesta del usuario**: "que lo elija cada persona" |
| RF6 (arrancan encendidas) | **Respuesta del usuario**: "todo encendido, y se apaga" |
| RF8 (los tres tipos) | **Respuesta del usuario**, menú confirmado en discovery |
| RF9 (ediciones no notifican) | **Respuesta del usuario** + `docs/PLAN_FASES.md` F2.E, control de volumen |
| RF10 (visibilidad) | HECHO: `pins/selectors.py` y D-001/F2.A ya en producción |
| RF11 (bloqueo) | HECHO: `accounts/services/friendships.py` con Block, F2.B en producción |
| RF12–RF16 (cola) | **Respuesta del usuario**: tabla en Postgres + cron. Config real de Redis verificada en `docker-compose.aws.yml` |
| RF17, RF18 (idioma) | HECHO verificado en discovery: el idioma no se persiste, sólo viaja en el request |
| RF19 (permiso en contexto) | `[ASSUMPTION]` — Android 13+ no repregunta tras un rechazo |
| RF20 (deep link) | HECHO: `docs/PLAN_FASES.md` F2.E lo marca como faltante |
| Fuera de alcance: email | **Respuesta del usuario**: punto único sí, migración no |
| Fuera de alcance: iOS | HECHO: bloqueado por el trámite de titularidad |
| Stack: FCM | HECHO: no hay alternativa en Android |

Un solo `[ASSUMPTION]` sobre 14 items: 7%.

## Sugerencias fuera de scope

- **Un "silencio nocturno"** por zona horaria. Hoy `TIME_ZONE` es Buenos Aires y
  los usuarios están en Hong Kong: una notificación a las 4 de la mañana es una
  desinstalación. No entra como RF porque nadie lo pidió, pero con usuarios en
  Asia y servidor en horario argentino, va a aparecer.
- **Migrar los emails a la cola** una vez que la cola tenga rodaje. Arreglaría
  el envío inline dentro del request, que es el antecedente que este bloque
  vino a no repetir.
