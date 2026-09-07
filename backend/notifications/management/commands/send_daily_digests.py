"""Manda el resumen diario a quien le toca en esta hora.

Corre **cada hora**, no cada minuto: recorre a quienes tienen el resumen
encendido y cuya hora local coincide con la que corre ahora. Con usuarios en
Hong Kong y el servidor en horario de Buenos Aires, "las siete de la tarde" no
es el mismo momento para todos.
"""

import logging

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

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
		candidates = User.objects.filter(
			is_active=True,
			profile__notify_daily_digest=True,
		).select_related("profile")

		forced = options["user"]
		if forced:
			candidates = candidates.filter(username=forced)

		sent = 0
		skipped = 0
		for user in candidates.iterator():
			if not forced and not digest.is_due(user.profile):
				skipped += 1
				continue
			if digest.send_for(user):
				sent += 1

		logger.info("send_daily_digests: enviados=%d fuera_de_hora=%d", sent, skipped)
		self.stdout.write(f"enviados={sent} fuera_de_hora={skipped}")
