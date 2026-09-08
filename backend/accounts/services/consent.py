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
	ConsentRecord.Policy.GDPR: "2026-05-28",
	ConsentRecord.Policy.PDPO: "2026-05-28",
	# DIGEST y TERMS nacen el 2026-09-08, cuando el resumen diario pasó a
	# pedirse en vez de venir encendido. La fecha es provisoria: el texto
	# publicado todavía no describe el resumen —ni le asigna base legal al
	# token push—, así que **cuando se publique la política reescrita hay que
	# revisar las cuatro versiones de acá**, no sólo las dos nuevas.
	ConsentRecord.Policy.DIGEST: "2026-09-08",
	ConsentRecord.Policy.TERMS: "2026-09-08",
}


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
