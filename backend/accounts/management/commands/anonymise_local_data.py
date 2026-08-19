"""Borra los datos personales de una base traída de producción.

Existe para que trabajar con datos reales no signifique tener los datos de
usuarios reales en un portátil. Se corre siempre junto con la restauración
—`make prod-snapshot` lo encadena— y nunca como un paso opcional que un día
uno se olvida.

**No puede correr contra producción.** El guard de abajo aborta si la base no
es local: es la única defensa entre un comando de conveniencia y borrar los
datos de todos los usuarios.
"""

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from accounts.models import ConsentRecord, EmailInvitation, Profile

# La base local corre en Docker: `db` desde el contenedor, localhost desde el
# host. Cualquier otra cosa —un endpoint de RDS, por ejemplo— no es local.
LOCAL_DB_HOSTS = {"db", "localhost", "127.0.0.1", "::1", ""}

# Password común para todas las cuentas del snapshot, para poder entrar con
# cualquiera mientras se desarrolla. Es seguro justamente porque este comando
# no puede tocar otra base que la local.
DEV_PASSWORD = "local-dev-1234"


class Command(BaseCommand):
	help = "Anonimiza usuarios, invitaciones y consentimientos en la base LOCAL."

	def handle(self, *args, **options):
		db_host = settings.DATABASES["default"].get("HOST", "")
		if db_host not in LOCAL_DB_HOSTS:
			raise CommandError(
				f"DB_HOST es {db_host!r}, que no es una base local. "
				"Este comando reescribe todos los usuarios: abortando."
			)

		user_model = get_user_model()

		with transaction.atomic():
			usuarios = 0
			for user in user_model.objects.all().iterator():
				user.username = f"user{user.pk}@local.test"
				user.email = f"user{user.pk}@local.test"
				user.first_name = f"Usuario {user.pk}"
				user.last_name = ""
				user.set_password(DEV_PASSWORD)
				user.save(
					update_fields=["username", "email", "first_name", "last_name", "password"]
				)
				usuarios += 1

			# El perfil guarda texto libre que la persona escribió sobre sí
			# misma, más sus redes y su teléfono. Nada de eso hace falta para
			# desarrollar y todo es identificable.
			perfiles = Profile.objects.update(bio="", website="", instagram="", phone="")

			# El email invitado es de alguien que puede ni siquiera tener cuenta.
			invitaciones = 0
			for invitacion in EmailInvitation.objects.all().iterator():
				invitacion.email = f"invitado{invitacion.pk}@local.test"
				invitacion.save(update_fields=["email"])
				invitaciones += 1

			# La IP es un dato personal y sólo se guarda como prueba legal del
			# consentimiento (GDPR/PDPO). Fuera de producción no prueba nada.
			consentimientos = ConsentRecord.objects.update(ip_address=None)

		self.stdout.write(
			self.style.SUCCESS(
				f"Anonimizados: {usuarios} usuarios, {perfiles} perfiles, "
				f"{invitaciones} invitaciones, {consentimientos} consentimientos.\n"
				f"Todas las cuentas quedaron con la contraseña: {DEV_PASSWORD}"
			)
		)
