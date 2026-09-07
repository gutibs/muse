"""Único lugar que le habla a Firebase Cloud Messaging.

Mismo patrón que `places/services/google_places.py`: acá vive la credencial y
el manejo de errores de `requests`, y nadie más arma una llamada HTTP a Google.

La API v1 **no tiene multicast**: es un request por token. Eso condiciona el
diseño del despachador y por eso `send_to_tokens` devuelve el resultado por
token en vez de un booleano.
"""

import logging

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

_SCOPE = "https://www.googleapis.com/auth/firebase.messaging"
_TIMEOUT = 10

# Lo que FCM devuelve cuando el token ya no sirve. No se reintenta: se borra.
# Sin esto la tabla se llena de teléfonos que no existen y cada envío se hace
# más lento.
#
# **`INVALID_ARGUMENT` NO está acá a propósito.** FCM lo devuelve para
# cualquier request malformada, no sólo por un token inválido: una clave
# reservada en `data`, un bloque `android` mal armado o un `FCM_PROJECT_ID` con
# forma equivocada devuelven lo mismo. Si estuviera en esta lista, un error de
# payload haría que el despachador borrara **todos los tokens de todos los
# usuarios**, uno por minuto, dejando como único rastro un `logger.info`. La
# recuperación sería que cada persona vuelva a iniciar sesión.
DEAD_TOKEN_ERRORS = frozenset({"UNREGISTERED", "NOT_FOUND"})


class FCMError(Exception):
	"""Falla al hablar con FCM. `dead_token` distingue reintentar de descartar."""

	def __init__(self, message: str, *, dead_token: bool = False):
		super().__init__(message)
		self.message = message
		self.dead_token = dead_token


class FCMNotConfiguredError(FCMError):
	"""Falta la service account. En dev es lo normal; en prod es un error."""


def _credentials():
	"""Credencial para hablar con FCM, cacheada por proceso.

	En producción el JSON es un config de **Workload Identity Federation**: el
	EC2 firma un `GetCallerIdentity` con su rol de IAM de AWS, Google lo valida
	contra el proveedor del pool y devuelve un token que impersona la service
	account. No hay clave privada en ninguna parte, que es lo que la política
	`iam.disableServiceAccountKeyCreation` de la organización obliga.

	El tipo sale del campo `type` del JSON. El camino de service account sigue
	acá por si algún día se puede volver a usar, pero hoy es teórico: esa key ni
	se puede generar.

	`google.auth` refresca el token solo cuando vence, así que alcanza con
	guardar el objeto. El import es local para que el proyecto siga
	importándose sin la dependencia cuando el push está apagado.
	"""
	global _CREDENTIALS
	if _CREDENTIALS is not None:
		return _CREDENTIALS

	raw = getattr(settings, "FCM_CREDENTIALS_JSON", "")
	if not raw:
		raise FCMNotConfiguredError("FCM_CREDENTIALS_JSON no está configurada")

	import json

	from google.auth.exceptions import GoogleAuthError

	try:
		info = json.loads(raw)
	except ValueError as exc:
		raise FCMNotConfiguredError(f"FCM_CREDENTIALS_JSON no es JSON válido: {exc}") from exc

	tipo = info.get("type") if isinstance(info, dict) else None
	if tipo not in ("external_account", "service_account"):
		raise FCMNotConfiguredError(
			f"FCM_CREDENTIALS_JSON: tipo de credencial desconocido ({tipo!r})"
		)

	# **Las constructoras directas, no `load_credentials_from_dict`.** El
	# helper genérico hace exactamente esto y después resuelve el project id
	# con un viaje a IMDS + STS + Resource Manager, para un project id que acá
	# no se usa: el nuestro es `FCM_PROJECT_ID`. Eso convertía el primer envío
	# de cada worker en tres round-trips que se cuelgan dos minutos enteros
	# cuando el metadata service no contesta —medido: 3m45s en la suite—, y con
	# el despachador corriendo por cron cada minuto, las corridas se solapan.
	# Armadas así, la credencial es local y el único viaje pasa en `refresh()`,
	# que `_access_token` ya envuelve.
	try:
		if tipo == "external_account":
			from google.auth import aws

			_CREDENTIALS = aws.Credentials.from_info(info, scopes=[_SCOPE])
		else:
			from google.oauth2 import service_account

			_CREDENTIALS = service_account.Credentials.from_service_account_info(
				info, scopes=[_SCOPE]
			)
	except (GoogleAuthError, ValueError, KeyError, TypeError) as exc:
		raise FCMNotConfiguredError(
			f"FCM_CREDENTIALS_JSON no es una credencial válida: {exc}"
		) from exc

	return _CREDENTIALS


_CREDENTIALS = None


def _access_token() -> str:
	"""Token de acceso, refrescándolo si venció.

	El `except Exception` es deliberado y no es un catch mudo: `creds.refresh`
	puede fallar por una clave revocada, un reloj desfasado o un corte de red,
	y esas excepciones son de `google.auth`, no de este módulo. Sin traducirlas
	a `FCMError` se escapan de `run_pending`, matan el lote entero y dejan los
	jobs en `processing` para siempre — se liberan a los 10 minutos y vuelven a
	explotar, sin llegar nunca a `FAILED`.
	"""
	from google.auth.transport.requests import Request

	creds = _credentials()
	if not creds.valid:
		try:
			creds.refresh(Request())
		except FCMError:
			raise
		except Exception as exc:
			raise FCMError(f"no se pudo refrescar la credencial de FCM: {exc}") from exc
	return creds.token


def _endpoint() -> str:
	project = getattr(settings, "FCM_PROJECT_ID", "")
	if not project:
		raise FCMNotConfiguredError("FCM_PROJECT_ID no está configurada")
	return f"https://fcm.googleapis.com/v1/projects/{project}/messages:send"


def send(
	*, token: str, title: str, body: str, data: dict | None = None, channel_id: str | None = None
) -> None:
	"""Manda una notificación a un token. Lanza `FCMError` si no se pudo.

	`data` viaja como strings porque FCM sólo acepta strings ahí; convertir en
	el borde evita que cada llamador se acuerde.

	`channel_id` decide por qué canal de Android sale. Sin él, el sistema usa
	`fcm_fallback_notification_channel` —el que FCM inventa solo—, que se le
	muestra al usuario como "Miscellaneous", no vibra, y mete todo en la misma
	bolsa. El id tiene que existir en el teléfono: lo crea la app al arrancar.
	"""
	android: dict = {"priority": "high"}
	if channel_id:
		# Sólo si hay canal: un bloque `notification` vacío le da a FCM un
		# INVALID_ARGUMENT, que es el error que no se puede confundir con un
		# token muerto.
		android["notification"] = {"channel_id": channel_id}

	payload = {
		"message": {
			"token": token,
			"notification": {"title": title, "body": body},
			"data": {k: str(v) for k, v in (data or {}).items()},
			"android": android,
		}
	}

	try:
		response = requests.post(
			_endpoint(),
			json=payload,
			headers={"Authorization": f"Bearer {_access_token()}"},
			timeout=_TIMEOUT,
		)
	except requests.RequestException as exc:
		raise FCMError(f"no se pudo hablar con FCM: {exc}") from exc

	if response.status_code == 200:
		return

	# El detalle del error viene en un cuerpo JSON con un `errorCode` de FCM.
	# Distinguirlo importa: un token muerto se borra, un 503 se reintenta.
	code = ""
	try:
		body_json = response.json()
		details = body_json.get("error", {}).get("details", [])
		for detail in details:
			if "errorCode" in detail:
				code = detail["errorCode"]
				break
		message = body_json.get("error", {}).get("message", response.text[:200])
	except ValueError:
		message = response.text[:200]

	dead = code in DEAD_TOKEN_ERRORS or response.status_code == 404
	raise FCMError(f"FCM {response.status_code} {code}: {message}", dead_token=dead)
