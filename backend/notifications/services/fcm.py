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
DEAD_TOKEN_ERRORS = frozenset({"UNREGISTERED", "INVALID_ARGUMENT", "NOT_FOUND"})


class FCMError(Exception):
	"""Falla al hablar con FCM. `dead_token` distingue reintentar de descartar."""

	def __init__(self, message: str, *, dead_token: bool = False):
		super().__init__(message)
		self.message = message
		self.dead_token = dead_token


class FCMNotConfiguredError(FCMError):
	"""Falta la service account. En dev es lo normal; en prod es un error."""


def _credentials():
	"""Credencial de la service account, cacheada por proceso.

	`google.auth` refresca el token solo cuando vence, así que alcanza con
	guardar el objeto. El import es local para que el proyecto siga
	importándose sin la dependencia cuando el push está apagado.
	"""
	global _CREDENTIALS
	if _CREDENTIALS is not None:
		return _CREDENTIALS

	raw = getattr(settings, "FCM_SERVICE_ACCOUNT_JSON", "")
	if not raw:
		raise FCMNotConfiguredError("FCM_SERVICE_ACCOUNT_JSON no está configurada")

	import json

	from google.oauth2 import service_account

	try:
		info = json.loads(raw)
	except ValueError as exc:
		raise FCMNotConfiguredError(f"FCM_SERVICE_ACCOUNT_JSON no es JSON válido: {exc}") from exc

	_CREDENTIALS = service_account.Credentials.from_service_account_info(info, scopes=[_SCOPE])
	return _CREDENTIALS


_CREDENTIALS = None


def _access_token() -> str:
	from google.auth.transport.requests import Request

	creds = _credentials()
	if not creds.valid:
		creds.refresh(Request())
	return creds.token


def _endpoint() -> str:
	project = getattr(settings, "FCM_PROJECT_ID", "")
	if not project:
		raise FCMNotConfiguredError("FCM_PROJECT_ID no está configurada")
	return f"https://fcm.googleapis.com/v1/projects/{project}/messages:send"


def send(*, token: str, title: str, body: str, data: dict | None = None) -> None:
	"""Manda una notificación a un token. Lanza `FCMError` si no se pudo.

	`data` viaja como strings porque FCM sólo acepta strings ahí; convertir en
	el borde evita que cada llamador se acuerde.
	"""
	payload = {
		"message": {
			"token": token,
			"notification": {"title": title, "body": body},
			"data": {k: str(v) for k, v in (data or {}).items()},
			"android": {"priority": "high"},
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
