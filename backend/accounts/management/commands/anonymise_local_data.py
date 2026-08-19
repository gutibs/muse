"""Borra los datos personales de una base traída de producción.

Existe para que trabajar con datos reales no signifique tener los datos de
usuarios reales en un portátil. Se corre siempre junto con la restauración
—`make prod-snapshot` lo encadena— y nunca como un paso opcional que un día
uno se olvida.

**No puede correr contra producción.** El guard de abajo aborta si la base no
es local: es la única defensa entre un comando de conveniencia y borrar los
datos de todos los usuarios.
"""

from urllib.parse import urlsplit

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from accounts.models import ConsentRecord, EmailInvitation, Profile
from places.models import PlacePhoto
from restaurants.models import Restaurant

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

			# `image_url` se guarda absoluta (se construye con API_PUBLIC_URL),
			# así que un snapshot llega con las 26 URLs apuntando a
			# lovemuse.app: el entorno local le pediría las fotos a producción
			# y gastaría su caché y su cuota. Reapuntarlas es lo que hace que
			# probar en local sea de verdad local.
			# Las fotos cacheadas son filas que apuntan a archivos del volumen
			# del servidor, y el dump no los trae. Dejarlas es dejar registros
			# que prometen bytes que no existen; se vuelven a bajar solas.
			fotos_borradas = 0
			for foto in PlacePhoto.objects.all():
				# El archivo primero: un `queryset.delete()` no toca el storage
				# y deja los bytes huérfanos ocupando disco, con el agregado de
				# que Django no sobrescribe un archivo existente —le pone un
				# sufijo— así que la próxima descarga duplica en vez de pisar.
				foto.file.delete(save=False)
				foto.delete()
				fotos_borradas += 1

			base_local = settings.API_PUBLIC_URL.rstrip("/")
			fotos = 0
			for restaurante in Restaurant.objects.exclude(image_url="").iterator():
				partes = urlsplit(restaurante.image_url)
				if not partes.path.endswith("/places/photo/"):
					continue  # imagen externa cargada a mano: no es nuestra
				restaurante.image_url = f"{base_local}{partes.path}?{partes.query}"[:2000]
				restaurante.save(update_fields=["image_url"])
				fotos += 1

		self.stdout.write(
			self.style.SUCCESS(
				f"Anonimizados: {usuarios} usuarios, {perfiles} perfiles, "
				f"{invitaciones} invitaciones, {consentimientos} consentimientos.\n"
				f"{fotos} image_url reapuntadas a {base_local}\n"
				f"{fotos_borradas} fotos cacheadas descartadas (los archivos no vienen en el dump)\n"
				f"Todas las cuentas quedaron con la contraseña: {DEV_PASSWORD}"
			)
		)
