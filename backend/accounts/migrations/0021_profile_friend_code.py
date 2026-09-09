"""El código de amistad de F2.F, en los tres pasos que exige un UUID único.

Hacerlo en una sola `AddField` con `default=uuid.uuid4` sería un bug de
producción: Django evalúa el callable **una vez** y le escribe el mismo
UUID a todas las filas existentes, así que el índice único falla al
aplicarse —o, peor, si el unique llegara después, todos los perfiles
compartirían código y el QR de cualquiera agregaría al mismo desconocido—.

Por eso: agregar nullable y sin unique, poblar fila por fila, y recién
entonces exigir unicidad.
"""

import uuid

from django.db import migrations, models


def poblar_codigos(apps, schema_editor):
	Profile = apps.get_model("accounts", "Profile")
	for profile in Profile.objects.filter(friend_code__isnull=True).iterator():
		profile.friend_code = uuid.uuid4()
		profile.save(update_fields=["friend_code"])


def borrar_codigos(apps, schema_editor):
	Profile = apps.get_model("accounts", "Profile")
	Profile.objects.update(friend_code=None)


class Migration(migrations.Migration):
	dependencies = [
		("accounts", "0020_apagar_el_resumen_que_nadie_eligio"),
	]

	operations = [
		migrations.AddField(
			model_name="profile",
			name="friend_code",
			field=models.UUIDField(db_index=True, null=True),
		),
		migrations.RunPython(poblar_codigos, borrar_codigos),
		migrations.AlterField(
			model_name="profile",
			name="friend_code",
			field=models.UUIDField(db_index=True, default=uuid.uuid4, unique=True),
		),
	]
