# Recuperación de contraseña por código

**Estado: borrador v2, corregido tras revisión adversarial.** Toca
autenticación, así que por regla del proyecto va mini-spec previa y TDD. Las
seis decisiones de producto están cerradas (ver Trazabilidad).

Base: discovery del 2026-08-26 sobre el código real, y el critique que siguió.
Los cambios respecto de la v1 están al final, en "Qué cambió y por qué".

---

## 1 · Problema

Quien olvida su contraseña no tiene forma de volver a entrar. La pantalla de
login ofrece "¿Olvidaste tu contraseña?", pero abre un cartel que dice que el
reseteo "viene pronto" y pide escribir a una casilla de contacto. La única
salida real es que Gustavo entre por SSH al servidor y corra
`manage.py changepassword`.

Con las cuentas actuales eso alcanzó, porque los usuarios son dos. El beta
arranca la semana del **14 de septiembre** con 12 personas y posiblemente unas
30, que no conocen a nadie del proyecto y no tienen por qué esperar a que
alguien les atienda un mail. Sin esto, cada olvido de contraseña es una cuenta
perdida y un pedido de soporte manual.

## 2 · Usuarios y casos de uso

**Un solo rol: el usuario final de la app.** No hay pantalla de administración
involucrada, y el staff conserva el camino que ya tiene (el admin de Django,
que usa el SMTP configurado aparte).

| Caso | Qué hace |
|---|---|
| Olvidé mi contraseña | Pide un código a su email, lo tipea en la app y elige una nueva |
| Me equivoqué al tipear el código | Reintenta, hasta cinco veces |
| El código venció | Pide uno nuevo, que reemplaza al anterior |
| Escribí mal mi email | No recibe nada; la app no le confirma ni desmiente que esa cuenta exista |
| Sospecho que alguien entró a mi cuenta | Al resetear, las sesiones abiertas en otros dispositivos dejan de funcionar |

## 3 · Requisitos funcionales

### Pedir el código

**RF1 — Pedir un código.**
`POST /api/v1/auth/password-reset/` con `{email}`. Si existe una cuenta activa
con ese email, genera un código numérico de 6 dígitos y lo envía por email.
*Aceptación:* con un email registrado, se crea exactamente una fila de
`PasswordResetCode` y se llama al envío una vez.

**RF2 — Respuesta uniforme, sin excepciones.**
RF1 responde **siempre `200` con el mismo cuerpo**: exista o no la cuenta, y
**también cuando el envío del email falla**.
*Aceptación:* el status y el cuerpo son idénticos byte a byte en los tres
escenarios —cuenta existente, cuenta inexistente, y cuenta existente con el
envío fallando—. Con la cuenta inexistente no se crea fila ni se llama al
envío.

> Este requisito reemplaza al RF12 de la v1, que devolvía `502` si Resend
> fallaba. Los dos no podían coexistir: como el camino sin cuenta nunca llama a
> Resend, jamás puede dar `502`, así que ese status era en sí mismo el oráculo
> de enumeración que RF2 existe para cerrar.

**RF3 — Trabajo equivalente en los dos caminos.**
Cuando el email no corresponde a ninguna cuenta, se ejecuta igual un hash
descartable, para que la diferencia de tiempo entre los dos caminos no sea el
costo del hasheo.
*Aceptación:* el camino sin cuenta invoca el hasher una vez.

**RF4 — Cooldown por email destino.**
Un mismo email no puede recibir más de **3 códigos por hora**, contados sobre
la casilla destino y no sobre quien pide.
*Aceptación:* el cuarto pedido para el mismo email dentro de la hora no envía
nada y no crea fila, y aun así responde lo que exige RF2.

> Sin esto, el throttle por IP no impide inundar la casilla de otra persona con
> mails que salen de tu dominio, ni frena al que pide códigos en serie para
> probar un valor fijo contra cada uno.

**RF5 — Fallo de envío registrado.**
Si Resend falla, la fila queda marcada como no enviada y se loguea con nivel
`error` y contexto suficiente para reintentarlo a mano.
*Aceptación:* con el envío fallando, existe la fila con su marca y un registro
en el log; el usuario recibe lo que exige RF2.

### Canjear el código

**RF6 — Canjear.**
`POST /api/v1/auth/password-reset/confirm/` con `{email, code, newPassword}`.
La búsqueda es **primero por usuario y después por código**: nunca por código
solo. Si el código es válido, vigente y no usado, cambia la contraseña.
*Aceptación:* con dos usuarios que tengan el mismo código vivo, cada uno canjea
el suyo y ninguno puede usar el del otro.

**RF7 — Vigencia de 15 minutos.**
*Aceptación:* a los 14 minutos el canje funciona; a los 16 responde error y la
contraseña no cambia.

**RF8 — Cinco intentos, contados de forma atómica.**
Cada canje fallido incrementa el contador con una operación atómica en la base
(`F("attempts") + 1`), no leyendo y escribiendo desde Python. Al quinto fallo el
código queda inutilizable aunque no haya vencido.
*Aceptación:* cuatro fallos seguidos dejan el código canjeable con el valor
correcto; cinco lo invalidan. Y con cinco canjes fallidos **concurrentes**, el
contador queda en cinco: ninguno se pierde.

**RF9 — Un solo código vivo por usuario.**
Pedir un código nuevo invalida cualquier anterior que siga vigente.
*Aceptación:* pedido A, pedido B, el canje con A falla y con B funciona.

**RF10 — Un código se usa una vez.**
*Aceptación:* el segundo canje con el mismo código falla, incluso dentro de los
15 minutos.

**RF11 — El código nunca se guarda ni se registra en claro.**
Se persiste sólo su hash, con el mismo mecanismo que una contraseña.
*Aceptación:* ninguna columna de la fila contiene los 6 dígitos, y el código no
aparece en los logs.

**RF12 — La contraseña nueva pasa las validaciones del proyecto.**
Las mismas cuatro de `AUTH_PASSWORD_VALIDATORS` que aplica el registro.
*Aceptación:* una contraseña que el registro rechaza también se rechaza acá,
con el mismo formato de error.

### Efectos y entorno

**RF13 — El reset cierra las sesiones abiertas.**
Después de un canje exitoso, los access y refresh emitidos antes dejan de ser
aceptados, en todos los dispositivos.
*Aceptación:* un token obtenido antes del reset devuelve `401` en un endpoint
autenticado después del reset; uno obtenido después funciona.

> **Corregido durante la implementación.** `CHECK_REVOKE_TOKEN` se chequea sólo
> en `JWTAuthentication.get_user`; `TokenRefreshSerializer.validate` no lo mira.
> De fábrica, entonces, un refresh emitido antes del reset sigue siendo aceptado
> por `/token/refresh/` —y con `ROTATE_REFRESH_TOKENS` devuelve otro refresh,
> indefinidamente—, aunque los access que produce hereden el claim viejo y no
> autentiquen. Se cerró con `ThrottledTokenRefreshView`, que compara el claim
> contra el usuario antes de emitir. Verificado en simplejwt 5.5.1.

**RF14 — El rate limit cuenta por cliente real, no por el proxy.**
DRF tiene que resolver la IP del cliente detrás de nginx.
*Aceptación:* dos requests con `X-Forwarded-For` distintos se cuentan en cubos
separados; el límite de uno no agota el del otro.

> **El diagnóstico de esta spec estaba mal, y el arreglo que proponía no
> funciona.** Verificado contra `rest_framework/throttling.py::get_ident` y
> midiendo `api_settings.NUM_PROXIES`:
>
> 1. Sin `NUM_PROXIES`, DRF **no** cae a `REMOTE_ADDR` mientras haya
>    `X-Forwarded-For`: usa la cadena XFF entera como identidad. Los anónimos
>    no comparten un cubo — pasa algo peor. Como nginx appendea con
>    `$proxy_add_x_forwarded_for`, esa cadena arranca con lo que mandó el
>    cliente, así que un XFF distinto en cada request da un cubo nuevo en cada
>    request: el throttle se evade entero, hoy, en `login` y `register`.
> 2. `NUM_PROXIES = 1` a nivel de módulo en `settings.py` **no hace nada**: DRF
>    lee sus settings del dict `REST_FRAMEWORK`, y con el setting suelto puesto
>    en 1, `api_settings.NUM_PROXIES` seguía en `None`. Va dentro del dict.

**RF15 — El email sale en el idioma del usuario.**
Español, inglés o italiano, con el mismo mecanismo que la invitación.
*Aceptación:* con `es`, `en` e `it` se renderiza el template correspondiente;
con un valor desconocido cae al default sin romper.

**RF16 — El flujo vive dentro de la app.**
El modal de "¿Olvidaste tu contraseña?" pasa a ser un flujo de tres pasos:
email → código → contraseña nueva. No se agrega ninguna ruta pública nueva ni
se sirve la SPA por web fuera de `/shared/`.
*Aceptación:* el flujo se recorre sin salir de la app y `nginx/test-routes.sh`
sigue en verde sin cambios.

**RF17 — Los códigos vencidos se borran.**
Una tarea de mantenimiento elimina las filas vencidas o usadas con más de 30
días, sumada al cron que ya corre los domingos.
*Aceptación:* el command borra sólo lo vencido o usado con más de 30 días y
deja intacto lo vigente.

## 4 · Requisitos no funcionales

**Seguridad.** Scope de throttle propio, `password_reset`, en **5/hora** para el
pedido y **10/hora** para el canje. Junto con RF4 (cooldown por destino), RF8
(intentos atómicos) y RF11 (hash), son lo que hace que seis dígitos alcancen.
El throttle no protege sólo la cuenta: cada pedido cuesta un email real.

**Limitación aceptada — timing.** La respuesta es idéntica (RF2) y el costo del
hasheo se iguala (RF3), pero el camino con cuenta hace además una llamada HTTP
a Resend dentro del request. Eso deja una diferencia de latencia observable. Se
acepta: el envío sincrónico es lo que hay sin infraestructura de colas, y la
señal es ruidosa e imprecisa comparada con la que se cerró. **Queda declarado
acá para que sea una decisión y no un descuido.**

**Resiliencia.** La llamada a Resend lleva timeout explícito. Sin él, un Resend
lento ocupa workers de gunicorn esperando a un tercero.

**i18n.** Tres idiomas en el email y en las pantallas nuevas.

**Observabilidad.** Cada pedido y cada canje se loguean con `user_id` y
resultado, nunca con el código. Sin esto, "no me llega el mail" durante el beta
no tiene evidencia que mirar.

**Compatibilidad — hay un deslogueo único.** Activar la revocación (ver Stack)
invalida **todos los tokens vigentes**, porque fueron firmados sin el claim que
la validación exige. Todos los usuarios tienen que volver a entrar una vez.
Se acepta y **se despliega antes del beta**, cuando el padrón real son dos
cuentas. La alternativa —aceptar tokens sin el claim— dejaría un bypass
permanente de la revocación.

## 5 · Fuera de alcance

- **Cambiar la contraseña estando adentro.** Ya existe (`ChangePasswordView`) y
  no se toca. Nota: al activar la revocación, ese flujo **también** pasa a
  cerrar las otras sesiones, que es lo correcto y hoy no hace.
- **Recuperar el email olvidado.** Sigue siendo escribir a soporte.
- **Segundo factor.** No está pedido.
- **Link en el email en vez de código.** Descartado en discovery.
- **Cola de tareas para el envío.** Resolvería el timing y el bloqueo de
  workers, pero es infraestructura nueva (broker + worker) para un flujo de
  bajo volumen. Se revisa si el volumen lo justifica.
- **Notificar por email que la contraseña cambió.** Sugerido abajo.

## 6 · Edge cases

| Caso | Severidad | Manejo |
|---|---|---|
| Email inexistente | **Crítico** | Respuesta idéntica, sin fila ni envío (RF2), con hash descartable (RF3) |
| Cuenta anonimizada (`is_active=False`) | **Crítico** | Se trata como inexistente: ni código ni email |
| Fuerza bruta sobre un código | **Crítico** | 5 intentos atómicos (RF8) + throttle |
| Pedir códigos en serie para probar un valor fijo | **Crítico** | Cooldown por destino (RF4): 3/hora acota los tiros |
| Inundar la casilla de un tercero | **Crítico** | Mismo cooldown (RF4) |
| Enumerar por el status de un fallo de envío | **Crítico** | Cerrado por RF2: el fallo no cambia la respuesta |
| Cinco canjes fallidos concurrentes | Importante | `F()` en la base (RF8) |
| Dos usuarios con el mismo código vivo | Importante | Búsqueda por usuario primero (RF6) |
| El código se canjea justo al vencer | Importante | Comparación contra `expires_at` en UTC al momento del canje |
| Dos pedidos casi simultáneos | Importante | Gana el último (RF9), invalidación en la misma transacción |
| Resend caído | Importante | Respuesta normal (RF2), fila marcada y log (RF5) |
| Cambio de email entre pedir y canjear | Baja | El código queda inalcanzable; el usuario pide otro. Documentado, no se maneja |
| Contraseña nueva igual a la vieja | Nice-to-have | Se permite: rechazarla revela que acertó la anterior |
| Cierra la app entre el paso 2 y el 3 | Nice-to-have | El código vive sus 15 minutos; puede retomar |

## 7 · Riesgos

| Riesgo | Prob. | Impacto | Mitigación |
|---|---|---|---|
| El deslogueo del deploy cae con el beta empezado | Baja | Alto | Desplegar antes del 14/9; con dos cuentas reales el costo es nulo |
| Los emails caen en spam y el beta no puede entrar | Media | Alto | Verificar el dominio en Resend y probar contra Gmail y Outlook reales antes del 14/9 |
| `NUM_PROXIES` mal configurado deja falsificar la IP | Baja | Alto | nginx **appendea** con `$proxy_add_x_forwarded_for`, así que con `NUM_PROXIES=1` DRF toma la posición correcta. Va con test (RF14) |
| Cuota de Resend en el plan gratuito | Baja | Medio | Verificar el límite mensual antes del beta; RF4 acota el peor caso |
| Llegar tarde al 14/9 | Baja | Alto | El alcance se achicó respecto de la v1: sin modelo de Profile, sin serializer de token, sin clase de autenticación propia |

## 8 · Stack propuesto

Sin dependencias nuevas.

**Modelo `PasswordResetCode` en `accounts`**, con el código hasheado
(`django.contrib.auth.hashers`), `expires_at`, `attempts`, `used_at` y una marca
de envío. Se descartó reusar el patrón de `EmailInvitation` —UUID en claro, sin
expiración— porque ahí el token no protege nada y acá es una credencial.

Se descartó el `PasswordResetTokenGenerator` de Django: produce tokens largos
firmados, no códigos de seis dígitos, y no permite contar intentos.

**Envío por `accounts/services/email.py`**, con `send_password_reset_email` al
lado de `send_invitation_email`. Es regla del proyecto: los emails del producto
no pasan por `django.core.mail`. Seis templates nuevos siguiendo
`invitation.{es,en,it}.{html,txt}`.

**Invalidación de sesiones: `CHECK_REVOKE_TOKEN` de simplejwt.** La librería ya
trae exactamente esto. Con

```python
SIMPLE_JWT = {
    ...
    "CHECK_REVOKE_TOKEN": True,   # default: False
}
```

`Token.for_user` agrega un claim con el md5 del hash de la contraseña, y
`JWTAuthentication.get_user` lo compara contra el usuario en cada request —
usando el `User` que **ya trae de la base** para chequear `is_active`, así que
no agrega ni un query. Cambiar la contraseña cambia el hash, y con él todos los
tokens emitidos antes.

Esto reemplaza al contador de versión en `Profile` de la v1, que implicaba un
campo, una migración, un serializer de token propio, una clase de autenticación
propia y un query extra en cada request autenticado. La decisión de producto
—que el reset cierre las sesiones— no cambia; cambia que no hay que construirla.

Se descartó la blacklist oficial: agrega una app, dos tablas que crecen con cada
login y necesitan limpieza, y sólo alcanza a los tokens emitidos después de
instalarla.

**`"NUM_PROXIES": 1` dentro del dict `REST_FRAMEWORK`** para que los throttles
cuenten por cliente (RF14). Dentro del dict, no suelto en `settings.py`: ver la
nota bajo RF14.

**Frontend:** el modal de `login/+page.svelte:72` pasa a tres pasos. Las claves
`login.forgotPassword` y `login.forgotBody` ya existen en los tres idiomas;
`forgotBody` se reescribe.

## 9 · Trazabilidad

| RF / decisión | Origen |
|---|---|
| Problema, urgencia del 14/9 | Dicho por Gustavo |
| RF1, RF6 — los dos endpoints | Decisión: código de 6 dígitos en la app |
| RF2 — respuesta uniforme sin excepciones | Respuesta a la pregunta de enumeración + critique (contradicción RF2/RF12 de la v1) |
| RF3 — trabajo equivalente | Critique (timing) |
| RF4 — cooldown por destino | Critique (email bombing y pedidos en serie) |
| RF5 — fallo registrado | Consecuencia de RF2 |
| RF6 — búsqueda por usuario primero | Critique (colisión de códigos) |
| RF7 — 15 minutos | Respuesta a la pregunta de vigencia |
| RF8 — 5 intentos atómicos | Respuesta a la pregunta de vigencia + critique (race) |
| RF9, RF10 | `[ASSUMPTION]` — no se preguntó; sin ellos RF7 y RF8 se esquivan pidiendo códigos nuevos |
| RF11 — código hasheado | Decisión: tabla propia con el código hasheado |
| RF12 — validaciones de contraseña | `[ASSUMPTION]` — el registro ya las aplica; que el reset sea más permisivo sería un agujero |
| RF13 — cerrar sesiones | Respuesta a la pregunta de sesiones |
| RF14 — throttle por cliente real | Verificado: `NUM_PROXIES` ausente en `settings.py:1-240` |
| RF15 — tres idiomas | Verificado: la app y los emails ya son trilingües |
| RF16 — sin ruta web nueva | Decisión: código en la app, no link |
| RF17 — limpieza | Critique + verificado: el cron corre `prune_place_cache` y `prune_activity`, nada más |
| `CHECK_REVOKE_TOKEN` | Verificado en la librería instalada: `authentication.py` y `tokens.py` |
| Modelo propio, no `EmailInvitation` | Verificado: guarda UUID en claro y no expira |
| Envío por el service | Verificado: regla del CLAUDE.md |
| Modal de tres pasos | Verificado: `login/+page.svelte:72` y las claves i18n existentes |

**Dos items `[ASSUMPTION]` sobre veintiuno: 9,5%.**

## 10 · Qué cambió y por qué

| v1 | v2 | Motivo |
|---|---|---|
| `502` si Resend falla | Siempre `200`, fallo logueado | El `502` era un oráculo de enumeración: sólo puede darse en cuentas que existen |
| "tiempos que no permitan distinguir" | Hash equivalente + limitación declarada | El requisito original no tenía criterio verificable y pasaba los tests estando roto |
| Contador en `Profile` + serializer + auth propios | `CHECK_REVOKE_TOKEN` de simplejwt | La librería ya lo trae. Se elimina el campo, la migración, dos clases propias y un query por request |
| Sin cooldown por destino | RF4, 3/hora por email | El throttle por IP no frena el email bombing ni los pedidos en serie |
| Throttle "más estricto que login" | 5/hora y 10/hora, con `NUM_PROXIES` | No había número, y el mecanismo no funcionaba detrás de nginx |
| `attempts` sin especificar | `F()` atómico, con test de concurrencia | Cinco requests simultáneas evadían el tope |
| Búsqueda no especificada | Por usuario primero | Buscar por código permite cruzar cuentas si dos coinciden |
| Sin limpieza | RF17 en el cron | La tabla crecía para siempre con hashes de credenciales |

## Sugerencias fuera de scope

- **Avisar por email cuando la contraseña cambia.** Es la señal que le llega a
  alguien cuya cuenta fue tomada. Un séptimo template y una llamada más.
- **Cerrar el hueco de `deploy.yml`**, que no espera a `test.yml`: si algo de
  esto sale roto, el deploy no se entera. Se vio pasar el 2026-08-26.


## 11 · Correcciones surgidas de la implementación (2026-08-26)

Tres afirmaciones de la spec no sobrevivieron al contacto con las librerías.
Quedan acá para que la spec no siga diciendo lo que ya se sabe falso:

| Decía | Es | Consecuencia |
|---|---|---|
| Sin `NUM_PROXIES` DRF usa `REMOTE_ADDR` y todos comparten un cubo | Usa la cadena XFF entera, que el cliente controla | El throttle no está "mal repartido": se evade variando el header. Aplica a `login` y `register` desde siempre |
| `NUM_PROXIES = 1` en `settings.py` | DRF lee sus settings del dict `REST_FRAMEWORK`; suelto queda en `None` | El arreglo propuesto no habría cambiado nada, y nada avisa |
| `CHECK_REVOKE_TOKEN` cubre access y refresh | Sólo se chequea en `JWTAuthentication.get_user` | Un refresh viejo seguía siendo canjeable. Se agregó el chequeo en la view de refresh |

Y una decisión de implementación que la spec no cubría: las dos llamadas del
frontend van por un `api.postAnon` que no manda el header `Authorization`. DRF
corre la autenticación antes que el permiso, así que un endpoint `AllowAny`
responde `401` igual si el header trae un token inválido — y el deploy que
activa `CHECK_REVOKE_TOKEN` deja a **todo el mundo** con un token muerto
guardado, justo cuando van a usar este flujo.
