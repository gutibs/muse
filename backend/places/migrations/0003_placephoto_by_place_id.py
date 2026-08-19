"""La clave de PlacePhoto pasa de `(photo_ref, width)` a `(place_id, width)`.

Los photo refs de Google caducan, así que una clave basada en el ref identifica
la foto por un puntero que se invalida solo. El place_id es estable.

Se escribe a mano en vez de autogenerarse porque `makemigrations` no puede
saber si `place_id` es un campo nuevo o un rename de `photo_ref`: son las dos
cosas a la vez conceptualmente, y la respuesta correcta es "campo nuevo, el ref
queda como registro de con qué se bajaron los bytes".

Sin backfill a propósito: la tabla está vacía en producción (el ref vencido
impedía guardar la primera foto, que es cómo se descubrió todo esto).
"""

from django.db import migrations, models


class Migration(migrations.Migration):
	dependencies = [("places", "0002_placephoto")]

	operations = [
		migrations.RemoveConstraint(model_name="placephoto", name="uniq_place_photo_key"),
		migrations.AddField(
			model_name="placephoto",
			name="place_id",
			field=models.CharField(default="", max_length=255),
			preserve_default=False,
		),
		migrations.AlterField(
			model_name="placephoto",
			name="photo_ref",
			field=models.CharField(blank=True, max_length=1000),
		),
		migrations.AddConstraint(
			model_name="placephoto",
			constraint=models.UniqueConstraint(
				fields=("place_id", "width"), name="uniq_place_photo_key"
			),
		),
	]
