"""Manda el resumen diario a quien le toca en esta hora.

Corre **cada hora**, no cada minuto: recorre a quienes tienen el resumen
encendido y cuya hora local coincide con la que corre ahora. Con usuarios en
Hong Kong y el servidor en horario de Buenos Aires, "las siete de la tarde" no
es el mismo momento para todos.
"""

import logging

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db.models import Q
from django.utils import timezone

from notifications.services import digest

logger = logging.getLogger(__name__)
User = get_user_model()


class Command(BaseCommand):
	help = "Manda el resumen diario de actividad a quien le corresponda ahora"

	def add_arguments(self, parser):
		parser.add_argument(
			"--user",
			type=str,
			default="",
			help="Username o email, para probar con una sola persona sin esperar su hora",
		)

	def handle(self, *args, **options):
		# `now` se calcula UNA vez y se pasa a todo. Si se leyera dentro del
		# loop, una corrida que cruza el cambio de hora dejaría de coincidir
		# con la hora local de los que faltan, y esa gente pierde el resumen
		# del día sin que nadie se entere. Con un request HTTP por token y
		# timeout de 10s, cruzar la hora no es hipotético.
		now = timezone.now()

		candidates = User.objects.filter(
			is_active=True,
			profile__notify_daily_digest=True,
		).select_related("profile")

		forced = options["user"]
		if forced:
			# Username **o email**, como promete el help. Filtrar sólo por
			# username hacía que pasar un email no matcheara nada y el comando
			# informara `enviados=0` como si hubiera funcionado.
			candidates = candidates.filter(Q(username=forced) | Q(email__iexact=forced))

		sent = 0
		skipped = 0
		failed = 0
		for user in candidates.iterator():
			if not forced and not digest.is_due(user.profile, now=now):
				skipped += 1
				continue
			try:
				if digest.send_for(user, now=now):
					sent += 1
			except Exception:
				# Ancho a propósito: sin esto, una excepción inesperada en una
				# persona —una credencial revocada, un dato raro— corta la
				# corrida y deja sin resumen a todos los que venían después.
				# Y como la corrida siguiente ya no coincide con su hora local,
				# pierden el día entero.
				logger.exception("digest falló para el usuario %s", user.pk)
				failed += 1

		logger.info(
			"send_daily_digests: enviados=%d fuera_de_hora=%d fallidos=%d", sent, skipped, failed
		)
		self.stdout.write(f"enviados={sent} fuera_de_hora={skipped} fallidos={failed}")
