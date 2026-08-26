"""Borra los códigos de recuperación que ya no sirven.

La tabla guarda hashes de credenciales de un solo uso: una vez que el código
venció o se canjeó, la fila es material sensible sin utilidad. Corre desde el
cron de mantenimiento (deploy/cron/muse-maintenance):

    docker compose exec backend python manage.py prune_password_reset_codes
"""

from datetime import timedelta

from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q
from django.utils import timezone

from accounts.models import PasswordResetCode

MIN_RETENTION_DAYS = 1
DEFAULT_RETENTION_DAYS = 30


class Command(BaseCommand):
	help = "Prune spent password reset codes older than N days (default 30)."

	def add_arguments(self, parser):
		parser.add_argument(
			"--days",
			type=int,
			default=DEFAULT_RETENTION_DAYS,
			help="Delete used or expired codes older than this many days.",
		)

	def handle(self, *args, **options):
		days = options["days"]
		# Mismo blindaje que prune_activity: con --days 0 —lo que deja una env
		# var vacía en el cron— el cutoff se pone en `now` y el filtro se lleva
		# puesto todo lo vencido de hoy, incluido lo que alguien está por
		# canjear. Negativo es peor: el cutoff se va al futuro.
		if days < MIN_RETENTION_DAYS:
			raise CommandError(
				f"--days debe ser >= {MIN_RETENTION_DAYS} (recibido: {days}). "
				"Un valor menor borraría códigos que todavía pueden estar en uso."
			)

		cutoff = timezone.now() - timedelta(days=days)
		now = timezone.now()
		# Sólo lo gastado: usado, o vencido. Un código vigente nunca entra acá,
		# por viejo que sea el registro.
		deleted, _ = PasswordResetCode.objects.filter(
			Q(used_at__isnull=False) | Q(expires_at__lte=now),
			created_at__lt=cutoff,
		).delete()

		self.stdout.write(
			self.style.SUCCESS(
				f"Deleted {deleted} spent password reset code(s) older than {days}d."
			)
		)
