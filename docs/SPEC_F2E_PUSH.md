# Push notifications

**Estado: borrador v2, corregido tras revisión adversarial.** Estrena
infraestructura (una cola) y toca el envío de mensajes a terceros, así que va
mini-spec previa por regla del proyecto. Las cuatro decisiones de producto
están cerradas (ver Trazabilidad); lo que cambió respecto de la v1 está al
final, en "Qué cambió y por qué".

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

**RF5** — Un usuario conserva como máximo **5 dispositivos**; al registrar el
sexto se descarta el de `last_seen_at` más viejo. Y todo token que no se usa
hace 90 días se borra desde el cron de mantenimiento.
*Criterio*: registrar seis tokens deja cinco, sin el más viejo. El teléfono
que se cambió el año pasado y nunca hizo logout deja de recibir solo.

### Preferencias

**RF6** — Cada persona tiene tres preferencias independientes: solicitud de
amistad recibida, solicitud aceptada, actividad de un amigo. Se leen y escriben
por el perfil.
*Criterio*: el serializer las expone y un PATCH las cambia.

**RF7** — Las tres arrancan **encendidas**, incluidas las de los usuarios que
ya existen.
*Criterio*: un usuario nuevo tiene las tres en `true`; la migración deja en
`true` a los 15 actuales.

**RF8** — Una preferencia apagada corta el envío en el punto único, no en la
vista. Apagar "actividad de un amigo" no puede dejar de notificar una solicitud
de amistad.
*Criterio*: con una apagada y las otras dos encendidas, sólo se encola lo que
corresponde.

### Qué notifica y qué no

**RF9** — Se notifican exactamente tres cosas: `friendship_request`,
`friendship_accepted` y `friend_activity` (un amigo pineó o calificó).
*Criterio*: la lista de tipos es cerrada y está en un `TextChoices`.

**RF10** — **Las ediciones no notifican nunca.** `Activity.Verb.UPDATED` existe
y seguirá alimentando el feed, pero no genera push. Corregir una reseña tres
veces manda cero notificaciones.
*Criterio*: test dedicado — editar un pin tres veces deja el feed con tres
entradas y la cola vacía.

**RF11** — Un pin que no es visible para el destinatario no genera
notificación. La política de visibilidad de F2.A manda también acá: notificar
"tu amigo pineó un lugar" sobre un pin privado lo delata igual que mostrarlo.
*Criterio*: test crítico — pin con `visibility=private` u `only_friends` con un
no-amigo: cero notificaciones. Se resuelve reusando `visible_pin_filter`, no
con una condición nueva al lado.

**RF12** — **La visibilidad se vuelve a chequear en el momento de despachar, no
sólo al encolar.** Entre una cosa y la otra pasa al menos un minuto, y en ese
minuto el pin puede haber pasado a privado. Un job cuyo pin dejó de ser visible
para su destinatario se descarta como `discarded`, no se entrega.
*Criterio*: test crítico — encolar con el pin público, pasarlo a `private`,
correr el despachador: cero envíos y el job queda `discarded`. Sin esto, el
oráculo que F2.A cerró se reabre con un minuto de retraso.

**RF13** — Un bloqueo corta la notificación en las dos direcciones, y también
se revalida al despachar: `are_friends` ya devuelve False si hay `Block` (F2.B).
*Criterio*: test — bloquear entre el encolado y el despacho descarta el job.

### La cola

**RF14** — Ningún envío a FCM ocurre dentro de un request HTTP. El signal
escribe filas en `NotificationJob` con `transaction.on_commit()`; un comando
las despacha después.
*Criterio*: test que cuenta llamadas — un `POST /api/v1/pins/` con 20 amigos no
hace ninguna llamada HTTP saliente.

**RF15** — El fan-out se escribe con **un solo `bulk_create`**, no con un INSERT
por amigo.
*Criterio*: test con `assertNumQueries` — encolar para 20 amigos no hace 20
inserts. Mover N llamadas HTTP fuera del request no sirve de nada si se dejan N
inserts adentro.

**RF16** — `NotificationJob` tiene estados explícitos: `pending`, `processing`,
`sent`, `failed`, `discarded`. Un job en `processing` guarda `locked_at`, y el
despachador **libera lo que lleva más de 10 minutos tomado**.
*Criterio*: test — un job en `processing` con `locked_at` viejo vuelve a
`pending` en la corrida siguiente. Sin esto, cada deploy —que hace `down` +
`up`— deja tildados para siempre los jobs que estaban a mitad de camino.

**RF17** — Cada job lleva una **clave de idempotencia** `(kind, actor, pin o
friendship, destinatario)` con índice único. Restaurar un backup de la base no
puede volver a mandar lo ya entregado.
*Criterio*: test — reencolar el mismo evento para el mismo destinatario no crea
un segundo job. El deploy hace `pg_dump` antes de cada corrida, así que
restaurar es un escenario real, no teórico.

**RF18** — El despachador toma los trabajos con
`select_for_update(skip_locked=True)`, en lotes de tamaño fijo.
*Criterio*: dos despachadores en paralelo sobre la misma cola no mandan dos
veces el mismo job.

**RF19** — Un job que falla se reintenta con backoff hasta 3 veces y después
queda `failed` con el error guardado. Un fallo de un destinatario no aborta el
lote.
*Criterio*: con FCM devolviendo 500 para un token y 200 para otro, el segundo
se entrega y el primero queda para reintento.

**RF20** — **Un job de más de 6 horas se descarta en vez de entregarse.** Si el
despachador estuvo caído, nadie quiere recibir de golpe lo que pasó ayer.
*Criterio*: test de corte por antigüedad; el job queda `discarded` con motivo.

**RF21** — Los tokens que FCM rechaza como `UNREGISTERED` o `INVALID_ARGUMENT`
se borran. Sin esto la tabla se llena de basura y cada envío se hace más lento.
*Criterio*: con esa respuesta mockeada, la fila del token desaparece y el job
no se reintenta.

**RF22** — Los jobs terminados se borran después de 7 días, desde el mismo cron
de mantenimiento que ya limpia el resto.
*Criterio*: comando `prune_notification_jobs` con test de corte por fecha.

### Idioma y contenido

**RF23** — `Profile.language` persiste el idioma elegido y es la fuente para el
texto de la notificación. Hoy el idioma sólo viaja en el request
(`request.data.get("language")`), y el push lo inicia el servidor: no hay
request del destinatario de donde sacarlo.
*Criterio*: con dos usuarios en idiomas distintos, el mismo evento produce dos
textos distintos.

**RF24** — El texto sale de `gettext` con `translation.override(...)`, el mismo
mecanismo que se puso el 2026-09-06 para los errores de la API, y los catálogos
`es`/`it` cubren los tres tipos.
*Criterio*: el test guardián de i18n sigue en verde y los mensajes nuevos están
en los `.po`.

**RF25** — Los nombres interpolados se truncan antes de armar el payload:
título hasta 65 caracteres, cuerpo hasta 240, con elipsis. En el catálogo real
hay nombres como "The Peppertree Restaurant - La Veranda Resort Phu Quoc
MGallery".
*Criterio*: test con el nombre más largo del catálogo; el payload entra en los
límites y el texto no queda cortado a la mitad de una palabra.

### La app

**RF26** — La app pide el permiso de notificaciones **después** de que la
persona hizo algo en Muse, no en el primer arranque. Android 13+ exige
`POST_NOTIFICATIONS` y un permiso negado no se vuelve a pedir.
*Criterio*: no se pide en el onboarding; se pide al mandar o aceptar la primera
solicitud de amistad.

**RF27** — Tocar una notificación abre la pantalla correspondiente: el perfil
de quien te solicitó, o la ficha del restaurante. Hoy no hay ningún manejo de
deep links.
*Criterio*: con la app cerrada y con la app en background, el tap lleva a la
ruta correcta.

**RF28** — La pantalla de ajustes distingue "apagado por vos" de "el sistema no
lo permite". Si Android tiene el permiso denegado, las tres preferencias pueden
estar encendidas y no llegar nada.
*Criterio*: con el permiso denegado, la pantalla lo dice y ofrece abrir los
ajustes del sistema.

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
- **i18n**: tres idiomas, sin excepción — ver RF23 y RF24.
- **Performance**: el `POST /pins/` no cambia su tiempo de respuesta (RF14,
  RF15). Sobre la latencia de entrega, ver abajo: **no está medida y por eso no
  se declara un número**.

### Latencia: lo que se sabe y lo que no

La v1 declaraba "hasta 2 minutos" sin haber medido nada. El número real depende
de tres cosas que todavía no se conocen: cuánto tarda `docker-compose exec` más
el arranque de Django en el t3.small, cuántos tokens tiene un lote, y cuánto
tarda cada request a FCM. **La API v1 de FCM no tiene multicast**: es un request
HTTP por token.

Por eso la primera tarea de implementación es **medir una corrida vacía y una
de 50 tokens en el EC2**, y recién con esos números fijar el tamaño de lote, la
concurrencia de envío y la frecuencia del cron. Si una corrida no entra
cómodamente en el intervalo, la decisión de cola vuelve a abrirse — un worker
residente en vez de cron es el plan B, y esta spec no lo cierra.

## 5 · Fuera de alcance

- **iOS.** El APNs key exige cuenta Apple Developer y eso está bloqueado por el
  trámite de titularidad con Jess. El diseño no se cierra contra iOS: `notify()`
  no asume FCM en su firma.
- **Migrar los emails existentes a la cola.** `notify()` nace como punto único
  pero hoy despacha sólo push. Invitación, reset y bienvenida se quedan como
  están: no se toca el path de auth en el mismo cambio que estrena una cola.
- **Notificaciones de marketing o novedades del producto.** Sólo los tres tipos
  de RF9.
- **Agrupación de notificaciones** ("3 amigos pinearon hoy"). Con 15 usuarios no
  hay volumen que lo justifique. Ver Riesgos: es lo primero que hay que revisar
  si el producto crece, porque rompe por producto antes que por infraestructura.
- **Silencio nocturno por huso horario.** Ver Riesgos: el servidor corre en
  horario de Buenos Aires y los usuarios están en Hong Kong.
- **Notificaciones en web.** La app no se sirve por web más allá de
  `/shared/<token>`.
- **Un panel para mandar notificaciones a mano desde el admin.** Es la puerta
  para el spam y no lo pidió nadie.

## 6 · Edge cases

| Caso | Severidad | Manejo |
|---|---|---|
| Pin privado o de sólo-amigos | **crítico** | RF11 al encolar y **RF12 al despachar** |
| El pin cambia a privado entre encolar y despachar | **crítico** | RF12: se descarta |
| Job tomado por un proceso que murió (deploy a mitad de lote) | **crítico** | RF16: `locked_at` y liberación a los 10 min |
| Restaurar un backup re-manda lo entregado | importante | RF17: clave de idempotencia única |
| El despachador no corre por horas | importante | RF20: los jobs viejos se descartan, no se acumulan |
| Dos cuentas en el mismo teléfono | importante | RF2: el token cambia de dueño |
| Un usuario con muchos dispositivos, o uno que ya no usa | importante | RF5: tope de 5 y limpieza a los 90 días |
| El token murió (app desinstalada) | importante | RF21: se borra ante UNREGISTERED |
| Nombre de restaurante larguísimo | importante | RF25: truncado explícito |
| La persona nunca aceptó el permiso de Android | importante | RF28: la pantalla lo distingue |
| Un amigo pinea 20 lugares seguidos | importante | Sin agrupación por decisión explícita. Ver Riesgos |
| FCM caído | importante | RF19: reintento con backoff |
| Bloqueo mutuo | crítico | RF13, al encolar y al despachar |
| Cuenta borrada entre el encolado y el envío | nice-to-have | El despachador revalida destinatario, preferencias y tokens |

## 7 · Riesgos

| Riesgo | Prob. | Impacto | Mitigación |
|---|---|---|---|
| La corrida no entra en el intervalo del cron | **media** | alto | Medir antes de fijar frecuencia (§4). Plan B declarado: worker residente |
| El cron por minuto con `docker-compose exec` pesa en un t3.small | media | medio | Un solo comando por lote, no uno por job. Se mide en la misma tarea |
| **Arrancar encendidas no alcanza como consentimiento GDPR** | media | alto | El permiso de Android autoriza mostrar, no procesar. Lo de uno a uno se sostiene como parte del servicio; "actividad de un amigo" es lo discutible. **Entra en la revisión legal que el plan ya tiene pendiente**, antes del release, no después |
| Notificar delata un pin privado | baja | **muy alto** | RF11 + RF12, con tests críticos |
| La política de privacidad queda sin actualizar | media | alto | Entra en la definición de terminado del bloque |
| Sin agrupación, el producto molesta antes de escalar | **alta si el producto crece** | alto | Aceptado para el volumen actual. Es lo primero a revisar; la alternativa del resumen diario está descrita en §8 |
| Notificación a las 4 de la mañana | **alta** | alto | Servidor en horario de Buenos Aires, usuarios en Hong Kong: once horas. Fuera de alcance por ahora y probablemente el primer pedido real |
| El permiso de Android se pide mal y se niega para siempre | media | alto | RF26: pedirlo en contexto |
| `Profile.language` nace vacío para los 15 actuales | alta | bajo | La migración usa `en`, default de la app; la app lo actualiza al abrir |

## 8 · Stack propuesto

- **FCM HTTP v1** con una service account. No hay alternativa en Android: es el
  único transporte que el sistema operativo acepta. **Una llamada HTTP por
  token** — la v1 no tiene multicast, y eso condiciona el diseño del
  despachador (§4).
- **Cola: tabla `NotificationJob` en Postgres + management command
  `dispatch_notifications` desde el cron existente.**
- **App `notifications` en Django**, con `services/dispatch.py::notify(user,
  kind, context)` como único punto de salida, siguiendo el patrón de los
  services canónicos del proyecto.
- **`@capacitor/push-notifications`** en el frontend. El andamiaje de Gradle ya
  está.
- **Dependencia nueva**: `google-auth` para firmar el token de la service
  account, con lo que arrastra. La v1 decía "sin dependencias nuevas" y en la
  misma línea agregaba una; queda dicho de frente.

### Alternativas descartadas

**Redis + RQ.** El Redis desplegado corre con `--save ""` y
`--maxmemory-policy allkeys-lru`: pierde trabajos en un restart y puede
perderlos por desalojo. Sirve como caché, que es para lo que se eligió. Un
segundo Redis dedicado significa otro contenedor y otro proceso en un t3.small
de 2 GB que ya corre nginx, gunicorn con 3 workers y el Redis de caché.

**Celery.** Broker, worker y configuración para lo que hoy son decenas de
notificaciones por día.

**Topics de FCM como cola.** Cada dispositivo se suscribe a un topic por usuario
y FCM hace el fan-out: desaparecen la tabla, el cron y los N inserts. Se pierde
el control de preferencias del lado servidor, la auditoría y el reintento. Para
un producto que audita todo lo demás, ese precio no cierra — pero es la
alternativa más barata si el despachador resulta inviable en el t3.small.

**Resumen diario en vez de push por evento.** Un job por persona por día ("3
amigos guardaron lugares nuevos"), a una hora que elige ella. Elimina el
fan-out, elimina la agrupación como deuda futura y resuelve gratis el problema
del huso horario. Pierde la inmediatez, que para "te mandaron una solicitud" sí
importa. **La combinación —inmediato lo de uno a uno, diario lo de actividad—
es probablemente mejor que lo que esta spec propone**, y no se adoptó porque
cambia una decisión de producto ya tomada. Queda acá para que se decida a
sabiendas.

## 9 · Trazabilidad

| RF / decisión | Origen |
|---|---|
| RF1–RF4 (registro de dispositivo) | Necesario para cualquier push; patrón estándar de FCM |
| RF5 (tope de dispositivos) | Revisión adversarial: el teléfono viejo sigue recibiendo |
| RF6, RF8 (preferencias por tipo) | **Respuesta del usuario**: "que lo elija cada persona" |
| RF7 (arrancan encendidas) | **Respuesta del usuario**: "todo encendido, y se apaga" |
| RF9 (los tres tipos) | **Respuesta del usuario**, menú confirmado en discovery |
| RF10 (ediciones no notifican) | **Respuesta del usuario** + `docs/PLAN_FASES.md` F2.E |
| RF11 (visibilidad al encolar) | HECHO: `pins/selectors.py`, D-001/F2.A en producción |
| RF12 (visibilidad al despachar) | Revisión adversarial: el pin puede cambiar en el intervalo |
| RF13 (bloqueo) | HECHO: `accounts/services/friendships.py` con Block, F2.B |
| RF14 (fuera del request) | **Respuesta del usuario** + plan F2.E |
| RF15 (bulk_create) | Revisión adversarial: N inserts en el request |
| RF16 (estados y zombis) | Revisión adversarial: el deploy hace `down` en cada push |
| RF17 (idempotencia) | Revisión adversarial: el deploy hace `pg_dump`, restaurar es real |
| RF18, RF19, RF21, RF22 (cola) | **Respuesta del usuario**: tabla + cron. Config de Redis verificada |
| RF20 (TTL) | Revisión adversarial: notificaciones de ayer llegando juntas |
| RF23 (idioma persistido) | HECHO verificado en discovery: hoy sólo viaja en el request |
| RF24 (gettext) | HECHO: mecanismo puesto el 2026-09-06 |
| RF25 (truncado) | Revisión adversarial + nombres reales del catálogo |
| RF26 (permiso en contexto) | `[ASSUMPTION]` — Android 13+ no repregunta tras un rechazo |
| RF27 (deep link) | HECHO: el plan lo marca como faltante |
| RF28 (permiso denegado visible) | Revisión adversarial: preferencia encendida sin permiso |
| Latencia sin número | Revisión adversarial: la v1 declaraba 2 minutos sin medir |

Un solo `[ASSUMPTION]` sobre 22 items: 5%.

## Sugerencias fuera de scope

- **Silencio nocturno** por zona horaria, en cuanto haya un usuario que lo pida
  — y va a pasar antes de lo que parece.
- **Migrar los emails a la cola** una vez que la cola tenga rodaje.

## 10 · Qué cambió y por qué

La v1 pasó por revisión adversarial y sacó 6/10. Tres huecos cambiaban código y
están cerrados:

1. **La visibilidad no se revalidaba al despachar** (ahora RF12). Entre encolar
   y enviar pasa al menos un minuto; pasar un pin a privado en ese intervalo
   dejaba salir la notificación igual. Era el oráculo de F2.A reabierto con un
   minuto de retraso, y la propia v1 lo listaba como riesgo "muy alto" mientras
   dejaba la puerta abierta.
2. **No había estados ni recuperación de jobs zombi** (ahora RF16). El deploy
   hace `down` + `up` en cada push: un job tomado por un proceso que muere
   quedaba tildado para siempre.
3. **La latencia estaba declarada sin medir** ("hasta 2 minutos"). Ahora no hay
   número: hay una tarea de medición como primer paso y un plan B declarado.

Además: `bulk_create` en el fan-out (RF15), clave de idempotencia para
sobrevivir a una restauración de backup (RF17), TTL de jobs viejos (RF20), tope
y limpieza de dispositivos (RF5), truncado de nombres (RF25), la distinción
entre "apagado por vos" y "el sistema no lo permite" (RF28), el riesgo de
consentimiento GDPR explicitado, y la contradicción de "sin dependencias
nuevas" corregida.

Lo que la revisión propuso y **no** se adoptó: el esquema mixto de inmediato
para uno a uno y resumen diario para actividad de amigos. Resuelve de una el
fan-out, la agrupación y el huso horario, pero cambia una decisión de producto
ya tomada. Queda documentado en §8 para decidirlo a sabiendas.
