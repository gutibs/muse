"""Consentimientos: qué versión rige y cómo se deja constancia.

Vivía en `accounts/consent.py` como una constante suelta. Se movió acá al
sumarle la escritura: dos módulos llamados `consent` —uno con la versión y otro
con el registro— es la duplicación que este proyecto trata de evitar.

Un `ConsentRecord` es evidencia: GDPR y PDPO exigen poder demostrar *cuándo* y
*a qué versión* alguien consintió, así que se escribe siempre por acá, nunca
armando el modelo a mano en una view.
"""

from accounts.models import ConsentRecord

# Versión vigente de cada política. Bumpear cuando cambia el texto legal
# correspondiente (ver `nginx/landing/{gdpr,pdpo}.html`); una versión nueva
# significa que los usuarios existentes tendrían que volver a consentir.
# Con fecha para que la versión apunte a un texto publicado concreto.
POLICY_VERSIONS = {
	# Las cuatro en 2026-09-08: ese día los textos publicados pasaron a
	# describir las notificaciones —el resumen diario con el consentimiento
	# como base, y las dirigidas a la persona por contrato— y a reconocerle al
	# usuario de Hong Kong el opt-out de analítica que la app ya le daba.
	# Bumpear GDPR y PDPO es lo que hace que las cuentas existentes vuelvan a
	# aceptar: la firma vieja es sobre un texto que ya no es el que rige.
	ConsentRecord.Policy.GDPR: "2026-09-08",
	ConsentRecord.Policy.PDPO: "2026-09-08",
	ConsentRecord.Policy.DIGEST: "2026-09-08",
	ConsentRecord.Policy.TERMS: "2026-09-08",
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
	"""La IP del cliente, mirando primero el proxy.

	Producción sirve detrás de nginx, así que `REMOTE_ADDR` es el proxy y la IP
	real viaja en `X-Forwarded-For`. Se toma la primera de la cadena.
	"""
	if request is None:
		return None
	forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
	if forwarded:
		return forwarded.split(",")[0].strip()
	return request.META.get("REMOTE_ADDR")


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
