# Push notifications

**Estado: borrador v3.** Estrena infraestructura (una cola) y toca el envío de
mensajes a terceros, así que va mini-spec previa por regla del proyecto. Las
decisiones de producto están cerradas (ver Trazabilidad); lo que cambió en cada
versión está al final, en "Qué cambió y por qué".

**El esquema es mixto**: lo dirigido a una persona llega al instante, la
actividad de los amigos llega una vez por día a la hora que cada uno elige.

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

| Caso | Canal | Quién recibe |
|---|---|---|
| Recibo una solicitud de amistad | inmediato | el destinatario, uno |
| Me aceptan una solicitud | inmediato | quien la había mandado, uno |
| Mis amigos guardaron lugares hoy | resumen diario | yo, uno por día |
| Elijo qué recibir y a qué hora | — | la propia persona |

Los dos canales son deliberadamente distintos. Lo dirigido a una persona es
esperado, de volumen bajo por naturaleza y pierde valor si llega tarde. La
actividad de los amigos es de uno a N, no es urgente, y agrupada molesta menos
y se lee mejor.

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

### Preferencias y horario

**RF6** — Cada persona tiene tres preferencias independientes: solicitud de
amistad recibida, solicitud aceptada, resumen diario de actividad.
*Criterio*: el serializer las expone y un PATCH las cambia.

**RF7** — Las tres arrancan **encendidas**, incluidas las de los usuarios que
ya existen.
*Criterio*: un usuario nuevo tiene las tres en `true`; la migración deja en
`true` a los 15 actuales.

**RF8** — Una preferencia apagada corta el envío en el punto único, no en la
vista.
*Criterio*: con una apagada y las otras dos encendidas, sólo sale lo que
corresponde.

**RF9** — `Profile.timezone` (IANA, ej. `Asia/Hong_Kong`) y
`Profile.digest_hour` (0–23, hora local, default **19**) definen cuándo llega
el resumen. La app manda la zona horaria del dispositivo al iniciar sesión; la
hora la elige la persona en Ajustes.
*Criterio*: dos usuarios en husos distintos con la misma `digest_hour` reciben
el resumen en momentos distintos, cada uno a su hora local.

Sin esto el resumen se manda en horario del servidor, que corre en
`America/Argentina/Buenos_Aires` mientras los usuarios están en Hong Kong:
once horas de diferencia y una notificación a las cuatro de la mañana.

### Qué notifica y qué no

**RF10** — Se notifican exactamente tres cosas: `friendship_request`,
`friendship_accepted` (las dos inmediatas) y `friend_activity_digest` (diario).
*Criterio*: la lista de tipos es cerrada y está en un `TextChoices`.

**RF11** — **Las ediciones no cuentan.** `Activity.Verb.UPDATED` alimenta el
feed pero no entra en el resumen ni genera notificación. Corregir una reseña
tres veces no le llega a nadie.
*Criterio*: test dedicado — editar un pin tres veces deja el feed con tres
entradas y el resumen del día sin nada.

**RF12** — El resumen incluye sólo lo que el destinatario **puede ver en el
momento en que se arma**: se construye con `visible_pin_filter`, la misma
política de F2.A, sobre la actividad de las últimas 24 horas.
*Criterio*: test crítico — un pin que estaba público y pasó a privado antes de
la hora del resumen no aparece. Notificar "tu amigo guardó un lugar" sobre un
pin que no podés ver lo delata igual que mostrarlo.

**RF13** — El resumen respeta el bloqueo: `are_friends` ya devuelve False si
hay `Block` (F2.B), y el resumen se arma sobre esa función, no sobre una
consulta nueva.
*Criterio*: test — con bloqueo activo, la actividad del bloqueado no aparece en
el resumen del otro.

**RF14** — Si en las últimas 24 horas no hay nada visible, **no se manda nada**.
No existe el resumen vacío.
*Criterio*: test — sin actividad, cero envíos y cero jobs.

### Las inmediatas: la cola

**RF15** — Ningún envío a FCM ocurre dentro de un request HTTP. El signal
escribe una fila en `NotificationJob` con `transaction.on_commit()`; un comando
la despacha después.
*Criterio*: test que cuenta llamadas — mandar una solicitud de amistad no hace
ninguna llamada HTTP saliente dentro del request.

**RF16** — `NotificationJob` tiene estados explícitos: `pending`, `processing`,
`sent`, `failed`, `discarded`. Un job en `processing` guarda `locked_at`, y el
despachador **libera lo que lleva más de 10 minutos tomado**.
*Criterio*: test — un job en `processing` con `locked_at` viejo vuelve a
`pending` en la corrida siguiente. Sin esto, cada deploy —que hace `down` +
`up`— deja tildados para siempre los jobs que estaban a mitad de camino.

**RF17** — Cada job lleva una **clave de idempotencia**
`(kind, actor, objeto, destinatario)` con índice único. Restaurar un backup de
la base no puede volver a mandar lo ya entregado.
*Criterio*: test — reencolar el mismo evento para el mismo destinatario no crea
un segundo job. El deploy hace `pg_dump` antes de cada corrida, así que
restaurar es un escenario real, no teórico.

**RF18** — El despachador toma los trabajos con
`select_for_update(skip_locked=True)`, en lotes de tamaño fijo.
*Criterio*: dos despachadores en paralelo no mandan dos veces el mismo job.

**RF19** — Un job que falla se reintenta con backoff hasta 3 veces y después
queda `failed` con el error guardado. Un fallo de un destinatario no aborta el
lote.
*Criterio*: con FCM devolviendo 500 para un token y 200 para otro, el segundo
se entrega y el primero queda para reintento.

**RF20** — **Un job inmediato de más de 6 horas se descarta en vez de
entregarse.** Si el despachador estuvo caído, nadie quiere que le avisen ahora
de una solicitud de ayer.
*Criterio*: test de corte por antigüedad; el job queda `discarded` con motivo.

**RF21** — Los tokens que FCM rechaza como `UNREGISTERED` o `INVALID_ARGUMENT`
se borran. Sin esto la tabla se llena de basura y cada envío se hace más lento.
*Criterio*: con esa respuesta mockeada, la fila del token desaparece y el job
no se reintenta.

**RF22** — Los jobs terminados se borran después de 7 días, desde el cron de
mantenimiento que ya limpia el resto.
*Criterio*: comando `prune_notification_jobs` con test de corte por fecha.

**RF23** — El resumen diario **no pasa por la cola**: el comando horario lo arma
y lo manda en el mismo paso, porque armarlo antes sería guardar una foto que
puede quedar desactualizada. Sí registra que se mandó, para no mandar dos veces
el mismo día.
*Criterio*: test — dos corridas del comando en la misma hora para el mismo
usuario mandan un solo resumen.

### Idioma y contenido

**RF24** — `Profile.language` persiste el idioma elegido y es la fuente para el
texto. Hoy el idioma sólo viaja en el request
(`request.data.get("language")`), y el push lo inicia el servidor: no hay
request del destinatario de donde sacarlo.
*Criterio*: con dos usuarios en idiomas distintos, el mismo evento produce dos
textos distintos.

**RF25** — El texto sale de `gettext` con `translation.override(...)`, el mismo
mecanismo que se puso el 2026-09-06 para los errores de la API, y los catálogos
`es`/`it` cubren los tres tipos. El resumen usa plurales de gettext: "1 lugar
nuevo" y "3 lugares nuevos" no se arman concatenando.
*Criterio*: el test guardián de i18n sigue en verde; hay test de plural en los
tres idiomas.

**RF26** — Los nombres interpolados se truncan antes de armar el payload:
título hasta 65 caracteres, cuerpo hasta 240, con elipsis. En el catálogo real
hay nombres como "The Peppertree Restaurant - La Veranda Resort Phu Quoc
MGallery".
*Criterio*: test con el nombre más largo del catálogo; el payload entra en los
límites y el texto no queda cortado a la mitad de una palabra.

### La app

**RF27** — La app pide el permiso de notificaciones **después** de que la
persona hizo algo en Muse, no en el primer arranque. Android 13+ exige
`POST_NOTIFICATIONS` y un permiso negado no se vuelve a pedir.
*Criterio*: no se pide en el onboarding; se pide al mandar o aceptar la primera
solicitud de amistad.

**RF28** — Tocar una notificación abre la pantalla correspondiente: el perfil
de quien te solicitó, o el feed en el caso del resumen. Hoy no hay ningún
manejo de deep links.
*Criterio*: con la app cerrada y con la app en background, el tap lleva a la
ruta correcta.

**RF29** — La pantalla de ajustes distingue "apagado por vos" de "el sistema no
lo permite". Si Android tiene el permiso denegado, las tres preferencias pueden
estar encendidas y no llegar nada.
*Criterio*: con el permiso denegado, la pantalla lo dice y ofrece abrir los
ajustes del sistema.

## 4 · Requisitos no funcionales

- **Privacidad (GDPR/PDPO)**: el token de dispositivo es dato personal y Google
  entra como procesador. Hay que declararlo en `nginx/landing/privacy.html` en
  los tres idiomas **en el mismo release**, no después. El cuerpo de la
  notificación no lleva contenido sensible: dice quién y qué lugar, nunca el
  texto de una reseña.
- **Seguridad**: no hay ninguna credencial de larga vida. El backend se
  autentica por Workload Identity Federation (§ 8.1), así que
  `FCM_CREDENTIALS_JSON` no lleva claves y no hay nada que rotar ni que se
  pueda filtrar. El allowlist de `gitleaks` cubre sólo `google-services.json` y
  no se amplía para esto.
- **Observabilidad**: cada envío deja una línea con tipo, destinatario y
  resultado. `LOGGING` ya existe desde el 2026-09-02.
- **i18n**: tres idiomas, sin excepción — ver RF24 y RF25.
- **Performance**: ningún request HTTP de usuario cambia su tiempo de respuesta.
  Sobre la latencia de entrega, ver abajo.

### Latencia: lo que se sabe y lo que no

La v1 declaraba "hasta 2 minutos" sin haber medido nada. El esquema mixto baja
mucho el problema —las inmediatas son un job por evento, no N— pero el número
sigue dependiendo de cuánto tarda `docker-compose exec` más el arranque de
Django en el t3.small. **La API v1 de FCM no tiene multicast**: es un request
HTTP por token, y una persona puede tener hasta cinco.

Primera tarea de implementación: **medir una corrida vacía y una de 20 jobs en
el EC2**, y con esos números fijar tamaño de lote y frecuencia del cron. Si no
entra cómodamente, el plan B es un worker residente en vez de cron, y esta spec
no lo cierra.

El resumen diario corre **por hora**, no por minuto: sólo procesa a quienes les
toca esa hora local. Ahí la latencia no importa.

## 5 · Fuera de alcance

- **iOS.** El APNs key exige cuenta Apple Developer y eso está bloqueado por el
  trámite de titularidad con Jess. El diseño no se cierra contra iOS: `notify()`
  no asume FCM en su firma.
- **Migrar los emails existentes a la cola.** `notify()` nace como punto único
  pero hoy despacha sólo push. Invitación, reset y bienvenida se quedan como
  están: no se toca el path de auth en el mismo cambio que estrena una cola.
- **Notificaciones de marketing o novedades del producto.** Sólo los tres tipos
  de RF10.
- **Notificación inmediata por actividad de un amigo.** Es el resumen diario, y
  es una decisión de diseño, no una simplificación: evita el fan-out, hace
  innecesaria la agrupación y saca el problema del horario.
- **Notificaciones en web.** La app no se sirve por web más allá de
  `/shared/<token>`.
- **Un panel para mandar notificaciones a mano desde el admin.** Es la puerta
  para el spam y no lo pidió nadie.

## 6 · Edge cases

| Caso | Severidad | Manejo |
|---|---|---|
| Un pin del resumen pasó a privado antes de la hora | **crítico** | RF12: el resumen se arma al mandarlo, no antes |
| Job tomado por un proceso que murió (deploy a mitad de lote) | **crítico** | RF16: `locked_at` y liberación a los 10 min |
| Bloqueo entre la actividad y el resumen | **crítico** | RF13: se arma sobre `are_friends` |
| Restaurar un backup re-manda lo entregado | importante | RF17: clave de idempotencia única |
| El despachador no corre por horas | importante | RF20: las inmediatas viejas se descartan |
| El comando horario no corre y se saltea una hora | importante | RF23: la marca de "ya mandado hoy" es por día, así que la corrida siguiente lo manda con retraso en vez de perderlo |
| Dos cuentas en el mismo teléfono | importante | RF2: el token cambia de dueño |
| Un usuario con muchos dispositivos, o uno que ya no usa | importante | RF5: tope de 5 y limpieza a los 90 días |
| El token murió (app desinstalada) | importante | RF21: se borra ante UNREGISTERED |
| Nadie hizo nada en 24 horas | importante | RF14: no se manda resumen vacío |
| Nombre de restaurante larguísimo | importante | RF26: truncado explícito |
| La persona nunca aceptó el permiso de Android | importante | RF29: la pantalla lo distingue |
| Zona horaria desconocida o inválida | importante | Default a UTC y la app la corrige al abrir |
| FCM caído | importante | RF19: reintento con backoff |
| Cuenta borrada entre el encolado y el envío | nice-to-have | El despachador revalida destinatario, preferencias y tokens |

## 7 · Riesgos

| Riesgo | Prob. | Impacto | Mitigación |
|---|---|---|---|
| La corrida no entra en el intervalo del cron | baja | alto | Medir antes de fijar frecuencia (§4). Plan B: worker residente. El esquema mixto ya sacó el fan-out, que era la fuente del volumen |
| **Arrancar encendidas no alcanza como consentimiento GDPR** | media | alto | El permiso de Android autoriza mostrar, no procesar. Lo de uno a uno se sostiene como parte del servicio; el resumen es lo discutible. **Entra en la revisión legal que el plan ya tiene pendiente**, antes del release |
| El resumen delata un pin que dejó de ser visible | baja | **muy alto** | RF12, con test crítico |
| La política de privacidad queda sin actualizar | media | alto | Entra en la definición de terminado del bloque |
| El resumen diario se vuelve ignorable | media | medio | Es el riesgo del canal: una notificación diaria que siempre dice lo mismo se apaga. Se mide con los eventos de analytics que ya existen |
| El permiso de Android se pide mal y se niega para siempre | media | alto | RF27: pedirlo en contexto |
| `Profile.language` y `timezone` nacen vacíos para los 15 actuales | alta | bajo | Migración con `en` y UTC; la app los actualiza al abrir |

## 8 · Stack propuesto

- **FCM HTTP v1**, autenticado por Workload Identity Federation (§ 8.1). No hay
  alternativa en Android: es el único transporte que el sistema operativo
  acepta. Una llamada HTTP por token.
- **Inmediatas**: tabla `NotificationJob` en Postgres + management command
  `dispatch_notifications` desde el cron existente.
- **Resumen**: management command `send_daily_digests`, horario, que arma y
  manda en el mismo paso.
- **App `notifications` en Django**, con `services/dispatch.py::notify(user,
  kind, context)` como único punto de salida, siguiendo el patrón de los
  services canónicos del proyecto.
- **`@capacitor/push-notifications`** en el frontend. El andamiaje de Gradle ya
  está.
- **Dependencia nueva**: `google-auth` para obtener el token de acceso, con lo
  que arrastra. La v1 decía "sin dependencias nuevas" y en la misma línea
  agregaba una; queda dicho de frente.

### 8.1 · Cómo se autentica el push

Sin service account key, **y no por elección**: la organización `dothecode.com`
tiene activa `iam.disableServiceAccountKeyCreation`, así que la clave no se
puede ni generar. Levantar esa política pedía asignarle a una persona
`roles/orgpolicy.policyAdmin` **a nivel organización** — permiso para desactivar
cualquier control de seguridad de la empresa, no sólo éste — para terminar
poniendo un archivo con una clave privada dentro del EC2. Se hizo lo que la
política empuja a hacer, que además es lo correcto.

**El camino que toma un push.** El EC2 lee sus credenciales temporales del
metadata service, firma con ellas un `GetCallerIdentity` de AWS STS y se lo
presenta a Google STS como prueba de identidad. Google valida el ARN contra el
proveedor del pool, devuelve un token federado, y ese token impersona la service
account de Firebase para sacar el access token con scope `firebase.messaging`.
La identidad la pone el rol de IAM de la instancia; no hay secreto en tránsito
ni en reposo.

**Lo que vive en GCP** (proyecto `muse-prod-498215`, todo a nivel proyecto —
ningún rol de organización, que es justamente lo que lo destraba): las APIs
`sts.googleapis.com` e `iamcredentials.googleapis.com`; el pool `muse-aws` y su
proveedor `muse-ec2`, con una `attribute-condition` atada al ARN exacto del rol de la
instancia; y `roles/iam.workloadIdentityUser` sobre la service account para el
principal de ese pool. La condición por ARN no es decorativa: sin ella, el
proveedor confía en la cuenta de AWS entera.

**Lo que vive en AWS**: un rol de IAM con instance profile en el EC2. Ese rol
**no necesita un solo permiso de AWS** — existe nada más para que
`GetCallerIdentity` devuelva un ARN estable que Google reconozca.

**Lo que vive en el código**: `FCM_CREDENTIALS_JSON` (antes
`FCM_SERVICE_ACCOUNT_JSON`; el nombre viejo mentía) con el config que escupe
`gcloud iam workload-identity-pools create-cred-config`. `_credentials()` elige
la constructora por el campo `type` y **no usa
`google.auth.load_credentials_from_dict`**: ese helper resuelve además el
project id con un viaje a IMDS + STS + Resource Manager, para un dato que acá no
se usa porque el nuestro es `FCM_PROJECT_ID`. Fuera de AWS eso no falla rápido,
se cuelga contra `169.254.169.254` hasta el timeout —dos minutos por llamada,
medidos— y con el despachador corriendo por cron cada minuto las corridas se
solapan. `test_armar_la_credencial_no_abre_ninguna_conexion` es el guardián de
eso.

### Alternativas descartadas

**Todo inmediato, con fan-out por evento** (lo que proponía la v2). Cada pin
encolaba un job por amigo. Traía tres problemas que el esquema mixto no tiene:
N inserts dentro del request, la agrupación como deuda futura inevitable, y la
notificación de las cuatro de la mañana. Se descartó al revisar la v2.

**Redis + RQ.** El Redis desplegado corre con `--save ""` y
`--maxmemory-policy allkeys-lru`: pierde trabajos en un restart y puede
perderlos por desalojo. Sirve como caché, que es para lo que se eligió. Un
segundo Redis dedicado significa otro contenedor y otro proceso en un t3.small
de 2 GB que ya corre nginx, gunicorn con 3 workers y el Redis de caché.

**Celery.** Broker, worker y configuración para lo que ahora son unos pocos
envíos por día.

**Topics de FCM como cola.** FCM haría el fan-out y desaparecería la tabla. Se
pierde el control de preferencias del lado servidor, la auditoría y el
reintento. Con el resumen diario el fan-out ya no existe, así que la ventaja
principal de los topics desapareció.

## 9 · Trazabilidad

| RF / decisión | Origen |
|---|---|
| RF1–RF4 (registro de dispositivo) | Necesario para cualquier push; patrón estándar de FCM |
| RF5 (tope de dispositivos) | Revisión adversarial: el teléfono viejo sigue recibiendo |
| RF6, RF8 (preferencias por tipo) | **Respuesta del usuario**: "que lo elija cada persona" |
| RF7 (arrancan encendidas) | **Respuesta del usuario**: "todo encendido, y se apaga" |
| RF9 (horario y zona) | **Respuesta del usuario**: esquema mixto con hora elegida |
| RF10 (los tres tipos) | **Respuesta del usuario**: inmediato lo de uno a uno, diario la actividad |
| RF11 (ediciones no cuentan) | **Respuesta del usuario** + `docs/PLAN_FASES.md` F2.E |
| RF12 (visibilidad al armar) | HECHO: `pins/selectors.py`, D-001/F2.A + revisión adversarial |
| RF13 (bloqueo) | HECHO: `accounts/services/friendships.py` con Block, F2.B |
| RF14 (sin resumen vacío) | Derivado del esquema de resumen |
| RF15 (fuera del request) | **Respuesta del usuario** + plan F2.E |
| RF16 (estados y zombis) | Revisión adversarial: el deploy hace `down` en cada push |
| RF17 (idempotencia) | Revisión adversarial: el deploy hace `pg_dump`, restaurar es real |
| RF18–RF22 (cola) | **Respuesta del usuario**: tabla + cron. Config de Redis verificada |
| RF23 (el resumen no se encola) | Derivado de RF12: una foto guardada queda vieja |
| RF24 (idioma persistido) | HECHO verificado en discovery: hoy sólo viaja en el request |
| RF25 (gettext y plurales) | HECHO: mecanismo puesto el 2026-09-06 |
| RF26 (truncado) | Revisión adversarial + nombres reales del catálogo |
| RF27 (permiso en contexto) | `[ASSUMPTION]` — Android 13+ no repregunta tras un rechazo |
| RF28 (deep link) | HECHO: el plan lo marca como faltante |
| RF29 (permiso denegado visible) | Revisión adversarial: preferencia encendida sin permiso |
| Latencia sin número | Revisión adversarial: la v1 declaraba 2 minutos sin medir |

Un solo `[ASSUMPTION]` sobre 22 items: 5%.

## Sugerencias fuera de scope

- **Migrar los emails a la cola** una vez que la cola tenga rodaje. Arreglaría
  el envío inline dentro del request, que es el antecedente que este bloque vino
  a no repetir.
- **Medir si el resumen se lee**, con los eventos de analytics que ya existen.
  Una notificación diaria que nadie toca es peor que ninguna.

## 10 · Qué cambió y por qué

### v3 — el esquema mixto

La actividad de los amigos pasó de notificación inmediata a **resumen diario a
la hora que elige cada persona**. Lo de uno a uno —solicitud recibida y
aceptada— sigue llegando al instante.

No es una simplificación: elimina tres problemas de raíz en vez de mitigarlos.
Desaparece el fan-out, y con él los N inserts dentro del request. Desaparece la
agrupación como deuda futura, porque el resumen **es** la agrupación. Y
desaparece la notificación de las cuatro de la mañana, porque la hora la elige
quien la recibe.

De regalo, la revalidación de visibilidad deja de ser un requisito aparte: el
resumen se arma en el momento de mandarlo, así que no existe el intervalo en el
que un pin podía pasar a privado entre encolar y enviar.

### v2 — correcciones de la revisión adversarial

La v1 sacó 6/10. Tres huecos cambiaban código: la visibilidad no se revalidaba
al despachar, no había estados ni recuperación de jobs zombi, y la latencia
estaba declarada sin medir. Se sumaron además idempotencia contra restauración
de backups, TTL de jobs viejos, tope y limpieza de dispositivos, truncado de
nombres, y la distinción entre "apagado por vos" y "el sistema no lo permite".

Dos cosas quedaron dichas en vez de tapadas: que arrancar encendidas no alcanza
como consentimiento GDPR para lo que no es transaccional, y que "sin
dependencias nuevas" era falso en la misma línea que agregaba `google-auth`.
