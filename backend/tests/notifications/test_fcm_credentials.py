"""Cómo consigue el backend la credencial para hablarle a FCM.

En producción el push se autentica por **Workload Identity Federation**: el EC2
prueba quién es con su propio rol de IAM de AWS y Google le devuelve un token.
No hay clave privada en ninguna parte — ni en el `.env`, ni en el repo, ni en
un secret de GitHub. Eso es lo que la política `iam.disableServiceAccountKeyCreation`
de la organización obliga, y es la razón por la que `FCM_CREDENTIALS_JSON`
dejó de ser un secreto: el config de WIF son URLs y un audience, nada más.

Ninguno de estos tests toca la red. Construir la credencial es local en los dos
formatos que `google.auth` reconoce; el viaje a Google recién pasa en
`refresh()`, y ese camino ya lo cubre `test_dispatch.py`.
"""

import json

import pytest
from django.test import override_settings

from notifications.services import fcm
from notifications.services.fcm import FCMNotConfiguredError

# Lo que escupe `gcloud iam workload-identity-pools create-cred-config`, con el
# pool y el proveedor de Muse. Está entero acá a propósito: si algún día alguien
# cambia la forma del config, este test dice exactamente qué campo se movió.
WIF_CONFIG = {
	"type": "external_account",
	"audience": (
		"//iam.googleapis.com/projects/742614029099/locations/global"
		"/workloadIdentityPools/muse-aws/providers/ec2"
	),
	"subject_token_type": "urn:ietf:params:aws:token-type:aws4_request",
	"service_account_impersonation_url": (
		"https://iamcredentials.googleapis.com/v1/projects/-/serviceAccounts"
		"/muse-push@muse-prod-498215.iam.gserviceaccount.com:generateAccessToken"
	),
	"token_url": "https://sts.googleapis.com/v1/token",
	"credential_source": {
		"environment_id": "aws1",
		"region_url": "http://169.254.169.254/latest/meta-data/placement/availability-zone",
		"url": "http://169.254.169.254/latest/meta-data/iam/security-credentials",
		"regional_cred_verification_url": (
			"https://sts.{region}.amazonaws.com?Action=GetCallerIdentity&Version=2011-06-15"
		),
		"imdsv2_session_token_url": "http://169.254.169.254/latest/api/token",
	},
}


@pytest.fixture(autouse=True)
def _sin_credencial_cacheada():
	"""La credencial se cachea por proceso: sin esto, el primer test gana."""
	fcm._CREDENTIALS = None
	yield
	fcm._CREDENTIALS = None


@override_settings(FCM_CREDENTIALS_JSON="")
def test_sin_credencial_configurada_el_push_queda_apagado():
	"""En dev es lo normal y no tiene que romper nada: apagado, no roto."""
	with pytest.raises(FCMNotConfiguredError):
		fcm._credentials()


@override_settings(FCM_CREDENTIALS_JSON="{esto no es json")
def test_un_json_roto_avisa_en_vez_de_explotar_cualquier_cosa():
	with pytest.raises(FCMNotConfiguredError) as exc:
		fcm._credentials()
	assert "JSON" in str(exc.value)


@override_settings(FCM_CREDENTIALS_JSON=json.dumps({"type": "algo_que_no_existe"}))
def test_un_config_que_google_no_reconoce_es_un_error_de_configuracion():
	"""El caso que rompía el lote entero.

	`load_credentials_from_dict` lanza `DefaultCredentialsError`, que no es
	`FCMError`. Sin traducirla acá se escapa de `run_pending`, mata el lote y
	deja los jobs en `processing` hasta que el barrido de zombis los libera —
	para volver a explotar igual. Es el mismo agujero que la revisión
	adversarial encontró con `RefreshError`, entrando por otra puerta.
	"""
	with pytest.raises(FCMNotConfiguredError):
		fcm._credentials()


@override_settings(FCM_CREDENTIALS_JSON=json.dumps(WIF_CONFIG))
def test_el_config_de_wif_produce_una_credencial_con_el_scope_de_fcm():
	creds = fcm._credentials()
	assert fcm._SCOPE in (creds.scopes or [])


@override_settings(FCM_CREDENTIALS_JSON=json.dumps(WIF_CONFIG))
def test_la_credencial_apunta_al_pool_que_le_pasamos():
	"""Guardián barato contra un config ignorado en silencio."""
	creds = fcm._credentials()
	assert "workloadIdentityPools/muse-aws" in creds._audience


@override_settings(FCM_CREDENTIALS_JSON=json.dumps(WIF_CONFIG))
def test_la_credencial_se_arma_una_sola_vez_por_proceso():
	"""`google.auth` refresca el token solo; rearmarla en cada envío tiraría
	el token vigente a la basura y sumaría un viaje a STS por notificación."""
	assert fcm._credentials() is fcm._credentials()


@override_settings(FCM_CREDENTIALS_JSON=json.dumps(WIF_CONFIG))
def test_el_config_de_wif_no_lleva_ninguna_clave_privada():
	"""El invariante que hace a todo esto valer la pena.

	Si alguien vuelve a meter una service account key en esta variable, este
	test lo dice. Es el único lugar donde la ausencia de la clave es el
	requisito, no un detalle.
	"""
	crudo = json.loads(fcm.settings.FCM_CREDENTIALS_JSON)
	assert crudo["type"] == "external_account"
	assert "private_key" not in crudo


@override_settings(FCM_CREDENTIALS_JSON=json.dumps({"type": "external_account"}))
def test_un_config_de_wif_incompleto_es_un_error_de_configuracion():
	"""Un `credential_source` faltante o de otro proveedor cae acá."""
	with pytest.raises(FCMNotConfiguredError):
		fcm._credentials()


@override_settings(FCM_CREDENTIALS_JSON=json.dumps(WIF_CONFIG))
def test_armar_la_credencial_no_abre_ninguna_conexion(monkeypatch):
	"""El guardián que justifica no usar `load_credentials_from_dict`.

	Ese helper resuelve el project id con un viaje a IMDS + STS + Resource
	Manager antes de devolver nada. Fuera de AWS eso no falla rápido: se cuelga
	contra 169.254.169.254 hasta el timeout —dos minutos por llamada, medidos
	en esta misma suite—, y adentro de AWS son tres round-trips por cada worker
	que arranca, para un dato que no usamos.

	Si alguien vuelve al helper genérico, este test lo dice al instante en vez
	de que se note como un cron que se solapa consigo mismo en producción.
	"""
	import socket

	def prohibido(*args, **kwargs):
		raise AssertionError("armar la credencial abrió una conexión de red")

	monkeypatch.setattr(socket.socket, "connect", prohibido)
	assert fcm._credentials() is not None
