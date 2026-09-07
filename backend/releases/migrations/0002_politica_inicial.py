"""La política de arranque para Android.

**Deliberadamente no bloquea a nadie**: `min_supported` queda en la primera
versión firmada que existió, así que el mecanismo entra en producción apagado.
Subir el piso deja gente afuera de verdad, y hoy `store_url` está vacío porque
las tiendas no están aprobadas: bloquear sin link a dónde ir es dejar a alguien
con una pantalla sin salida literal.

Cuando exista el link —tienda o descarga directa— se carga desde el admin, y ahí
recién tiene sentido subir el mínimo. Ese es todo el punto de que esto viva en la
base y no en el build.
"""

from django.db import migrations


def cargar_politica(apps, schema_editor):
	AppVersion = apps.get_model("releases", "AppVersion")
	AppVersion.objects.update_or_create(
		platform="android",
		defaults={
			"min_supported": "1.1.0",
			"latest": "1.4.1",
			"store_url": "",
		},
	)


def borrar_politica(apps, schema_editor):
	apps.get_model("releases", "AppVersion").objects.filter(platform="android").delete()


class Migration(migrations.Migration):
	dependencies = [("releases", "0001_initial")]

	operations = [migrations.RunPython(cargar_politica, borrar_politica)]
