"""Apaga el resumen diario a quien lo tenía sin haberlo pedido.

`notify_daily_digest` arrancaba en True y el alta no pregunta nada sobre
notificaciones, así que los 17 perfiles de producción lo tenían encendido sin
haberlo visto nunca. Como el resumen es actividad de terceros empujada al
teléfono —no algo que pasó con tu cuenta—, la base legal es el consentimiento,
y un default no es consentimiento.

Cambiar el default en el modelo no alcanza: sólo aplica a las filas nuevas. Sin
esta migración, exactamente las personas que ya estaban lo seguirían recibiendo.

`digest_prompt_seen` queda en False a propósito: es lo que hace que la app les
ofrezca encenderlo la próxima vez que la abran. Sin eso, el resumen les
desaparecería sin explicación.
"""

import logging

from django.db import migrations

logger = logging.getLogger(__name__)


def apagar_el_resumen(apps, schema_editor):
	Profile = apps.get_model("accounts", "Profile")
	ConsentRecord = apps.get_model("accounts", "ConsentRecord")

	# Se excluye a quien ya haya consentido explícitamente. Hoy no puede haber
	# ninguno —la política DIGEST nace en este mismo cambio— pero una migración
	# que apaga preferencias tiene que ser precisa sobre a quién toca, no
	# depender de cuándo se corre.
	ya_consintieron = ConsentRecord.objects.filter(policy="digest").values_list(
		"user_id", flat=True
	)
	apagados = (
		Profile.objects.filter(notify_daily_digest=True)
		.exclude(user_id__in=ya_consintieron)
		.update(notify_daily_digest=False, digest_prompt_seen=False)
	)
	logger.info("Resumen diario apagado en %s perfiles que no lo habían pedido", apagados)


def no_se_puede_volver(apps, schema_editor):
	"""Deliberadamente vacío.

	Volver atrás sería encenderle el resumen a gente que no lo pidió, que es
	justo lo que esta migración existe para deshacer. El estado anterior
	tampoco se puede reconstruir: nadie había elegido nada, todos estaban en el
	default.
	"""


class Migration(migrations.Migration):
	dependencies = [("accounts", "0019_profile_digest_prompt_seen_and_more")]

	operations = [migrations.RunPython(apagar_el_resumen, no_se_puede_volver)]
