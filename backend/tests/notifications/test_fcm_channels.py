"""Por qué canal de Android sale cada notificación.

Sin un canal propio, Android usa `fcm_fallback_notification_channel`: el que
FCM inventa cuando la app no declara ninguno. Eso se ve en el teléfono y no es
cosmético — verificado en un Galaxy S23+ con la V1.4.0:

- En Ajustes, Muse muestra un canal llamado **"Miscellaneous"**.
- Ese canal viene con `FLAG_MUTE_HAPTIC`: **no vibra**.
- Todo cae en el mismo lugar, así que no se puede silenciar el resumen diario
  sin silenciar también las solicitudes de amistad, que es exactamente la
  separación que el producto promete al tener dos canales distintos.

**El id tiene que coincidir con el que la app crea.** Si no coincide, Android no
falla: usa el fallback y nadie se entera. `push.service.test.ts` compara este
archivo contra el del frontend por esa razón.
"""

from unittest.mock import patch

import pytest
from django.test import override_settings

from notifications.models import NotificationJob
from notifications.services import dispatch, fcm


class RespuestaOk:
	status_code = 200

	@staticmethod
	def json():
		return {}


@override_settings(FCM_PROJECT_ID="proyecto-de-prueba")
def _payload_de(**kwargs) -> dict:
	"""Manda una notificación y devuelve el JSON que salió hacia FCM."""
	with patch.object(fcm, "_access_token", return_value="token-de-prueba"):
		with patch("notifications.services.fcm.requests.post", return_value=RespuestaOk()) as post:
			fcm.send(token="t", title="hola", body="mundo", **kwargs)
	return post.call_args.kwargs["json"]


def test_el_canal_viaja_en_el_bloque_android_del_mensaje():
	payload = _payload_de(channel_id=dispatch.CHANNEL_SOCIAL)
	assert payload["message"]["android"]["notification"]["channel_id"] == dispatch.CHANNEL_SOCIAL


def test_sin_canal_el_mensaje_sigue_siendo_valido():
	"""No se manda un `notification` vacío: FCM devuelve INVALID_ARGUMENT."""
	payload = _payload_de()
	assert "notification" not in payload["message"]["android"]


def test_la_prioridad_alta_sigue_estando():
	"""El canal se agrega al bloque android, no lo reemplaza."""
	payload = _payload_de(channel_id=dispatch.CHANNEL_SOCIAL)
	assert payload["message"]["android"]["priority"] == "high"


@pytest.mark.parametrize(
	"kind,esperado",
	[
		(NotificationJob.Kind.FRIENDSHIP_REQUEST, dispatch.CHANNEL_SOCIAL),
		(NotificationJob.Kind.FRIENDSHIP_ACCEPTED, dispatch.CHANNEL_SOCIAL),
	],
)
def test_cada_tipo_sale_por_su_canal(kind, esperado):
	assert dispatch.channel_for(kind) == esperado


def test_un_tipo_desconocido_cae_en_el_canal_social():
	"""Mejor el canal equivocado que el fallback sin vibración."""
	assert dispatch.channel_for("algo_que_no_existe") == dispatch.CHANNEL_SOCIAL


def test_los_dos_canales_son_distintos():
	"""Si fueran el mismo, silenciar uno silenciaría el otro."""
	assert dispatch.CHANNEL_SOCIAL != dispatch.CHANNEL_DIGEST


def test_los_ids_no_llevan_nada_raro():
	"""Android los usa como clave: un cambio deja el canal viejo huérfano en
	Ajustes y crea uno nuevo, así que conviene que sean simples y estables."""
	for canal in (dispatch.CHANNEL_SOCIAL, dispatch.CHANNEL_DIGEST):
		assert canal.replace("_", "").isalnum(), canal
		assert canal == canal.lower()
