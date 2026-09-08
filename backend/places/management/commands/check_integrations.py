"""Chequea que Google Places siga respondiendo y avisa cuando cambia.

Lo corre el cron cada 6 horas (`deploy/cron/muse-maintenance`):

    python manage.py check_integrations

Cada 6 y no cada hora por plata: Google regala 1.000 llamadas por SKU al mes y
un chequeo horario se come 720 de ellas: el 72% del cupo, gastado en
vigilancia, quitándoselo a la gente que busca restaurantes. Así son 120 al mes
y el corte se detecta el mismo día.

Vigila a Google, no a Muse: si el contenedor o el EC2 se caen, este comando no
corre y no avisa nadie. Eso necesita un pinger externo y es otro trabajo.
"""

from django.core.management.base import BaseCommand

from accounts.services.email import EmailSendError, send_integration_alert_email
from places.services import health


class Command(BaseCommand):
	help = "Check external integrations and email MODERATION_EMAIL when one changes state."

	def add_arguments(self, parser):
		parser.add_argument(
			"--no-retry",
			action="store_true",
			help="Fail on the first error instead of retrying once (for a quick manual check).",
		)

	def handle(self, *args, **options):
		result = health.probe_places(retries=0 if options["no_retry"] else 1)
		outcome = health.update_state(health.GOOGLE_PLACES, result)
		estado = "ok" if result.healthy else f"DOWN ({result.error})"

		if not outcome.should_alert:
			self.stdout.write(f"{health.GOOGLE_PLACES}: {estado}")
			return

		try:
			send_integration_alert_email(
				service=health.GOOGLE_PLACES,
				healthy=result.healthy,
				error=result.error,
				downtime=outcome.downtime,
			)
		except EmailSendError as exc:
			# A propósito sin `mark_alerted`: el estado queda pendiente y la
			# corrida de dentro de 6 horas reintenta el aviso. Marcarlo acá
			# consumiría el cambio de estado y el corte no se avisaría nunca.
			self.stderr.write(
				self.style.ERROR(f"{health.GOOGLE_PLACES}: {estado} — no se pudo avisar: {exc}")
			)
			return

		health.mark_alerted(outcome.state)
		aviso = "recuperación" if result.healthy else "caída"
		self.stdout.write(
			self.style.SUCCESS(f"{health.GOOGLE_PLACES}: {estado} — avisada la {aviso}")
		)
