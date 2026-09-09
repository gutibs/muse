"""Consentimientos: qué versión rige y cómo se deja constancia.

Vivía en `accounts/consent.py` como una constante suelta. Se movió acá al
sumarle la escritura: dos módulos llamados `consent` —uno con la versión y otro
con el registro— es la duplicación que este proyecto trata de evitar.

Un `ConsentRecord` es evidencia: GDPR y PDPO exigen poder demostrar *cuándo* y
*a qué versión* alguien consintió, así que se escribe siempre por acá, nunca
armando el modelo a mano en una view.
"""

import ipaddress
import logging

from rest_framework.throttling import BaseThrottle

from accounts.models import ConsentRecord

logger = logging.getLogger(__name__)

# Versión vigente de cada política. Bumpear cuando cambia el texto legal
# correspondiente (ver `nginx/landing/{gdpr,pdpo}.html`); una versión nueva
# significa que los usuarios existentes tendrían que volver a consentir.
# Con fecha para que la versión apunte a un texto publicado concreto.
POLICY_VERSIONS = {
	# GDPR y PDPO en 2026-09-08: ese día sus textos pasaron a describir las
	# notificaciones —el resumen diario con el consentimiento como base, las
	# dirigidas a la persona por contrato— y a reconocerle al usuario de Hong
	# Kong el opt-out de analítica que la app ya le daba. Bumpearlas es lo que
	# hace que las cuentas existentes vuelvan a aceptar: una firma sobre un
	# texto que ya no rige no prueba nada.
	ConsentRecord.Policy.GDPR: "2026-09-08",
	ConsentRecord.Policy.PDPO: "2026-09-08",
	# **TERMS NO se bumpeó**: `nginx/landing/terms.html` sigue siendo el del
	# 18 de mayo. La fecha tiene que apuntar a un documento publicado de verdad
	# — estampar una versión que no existe deja la evidencia señalando un texto
	# que nadie puede leer. Se bumpea cuando cambie ese archivo, no antes.
	ConsentRecord.Policy.TERMS: "2026-05-18",
	# DIGEST no es un documento sino una finalidad, y nace con este cambio.
	ConsentRecord.Policy.DIGEST: "2026-09-08",
}


# Los documentos que toda persona tiene que haber aceptado. DIGEST queda
# afuera a propósito: no es un documento legal sino una finalidad opcional, y
# no tenerlo aceptado es una elección válida, no una deuda.
LEGAL_POLICIES = (
	ConsentRecord.Policy.GDPR,
	ConsentRecord.Policy.PDPO,
	ConsentRecord.Policy.TERMS,
)


def pending_policies(user) -> list[str]:
	"""Qué documentos legales le faltan a `user` en su versión vigente.

	Existe por las cuentas anteriores a que hubiera registro: la migración que
	creó la tabla fue schema-only y sin backfill, así que 16 de los 17 perfiles
	de producción no tienen ninguna fila. También cubre el caso futuro de un
	texto nuevo: al bumpear la versión, la aceptación vieja deja de contar.
	"""
	aceptadas = set(
		user.consents.filter(policy__in=LEGAL_POLICIES).values_list("policy", "policy_version")
	)
	return [p for p in LEGAL_POLICIES if (p, POLICY_VERSIONS[p]) not in aceptadas]


def client_ip(request) -> str | None:
	"""La IP del cliente, resolviendo la cadena de proxies como corresponde.

	**No se toma la primera entrada de `X-Forwarded-For`.** Nginx sirve el API
	con `proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for`, que
	*agrega* la IP real al final de lo que mandó el cliente en vez de pisarlo:
	quien manda `X-Forwarded-For: 1.2.3.4` termina con `1.2.3.4, <ip real>`, y
	leer la primera es leer lo que el atacante escribió. Esta IP es evidencia de
	dónde se dio un consentimiento — falsificable no sirve de evidencia.

	Se delega en `get_ident` de DRF, que ya resuelve esto con `NUM_PROXIES` (1
	en producción) y es la única implementación del proyecto que lo hace bien;
	los throttles dependen de ella desde RF14. Se usa una clase de throttling
	para algo que no es throttling porque ahí vive el método, no por otra razón.
	"""
	if request is None:
		return None

	ident = BaseThrottle().get_ident(request)
	if not ident:
		return None

	# `ip_address` es `inet` en Postgres y `record_consent` escribe con
	# `bulk_create`, que no valida: un valor que no parsea no queda guardado
	# como basura, revienta el INSERT y devuelve un 500 en el alta. Y `get_ident`
	# puede devolver algo que no es una IP —la cadena entera unida— si
	# `NUM_PROXIES` quedara en None. La evidencia se degrada a None; perderla no
	# justifica dejar a alguien sin poder registrarse.
	try:
		ipaddress.ip_address(ident)
	except ValueError:
		logger.warning("Descartada una IP ilegible para el consentimiento: %r", ident)
		return None

	return ident


def record_consent(user, policies, ip_address=None) -> list[ConsentRecord]:
	"""Deja constancia de que `user` aceptó `policies` en este momento.

	Acepta una política o varias porque el alta registra GDPR y PDPO juntas
	—un solo checkbox, dos marcos legales— y encender el resumen diario
	registra una sola.

	No verifica si ya existe: son evidencia append-only, y volver a consentir
	agrega una fila en vez de pisar la anterior. Cuál rige es la última.
	"""
	if isinstance(policies, str):
		policies = [policies]

	return ConsentRecord.objects.bulk_create(
		[
			ConsentRecord(
				user=user,
				policy=policy,
				policy_version=POLICY_VERSIONS[policy],
				ip_address=ip_address,
			)
			for policy in policies
		]
	)
