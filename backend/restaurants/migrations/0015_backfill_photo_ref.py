"""Rellena `photo_ref` desde el `image_url` que ya estaba guardado.

Las filas viejas se importaron cuando el modelo no tenía el campo, así que el
ref sólo existe embebido en el query string de la URL del proxy de fotos. Sin
este backfill, todos los restaurantes existentes quedarían sin atribución
—que los términos de Google exigen mostrar— hasta que alguien los reimportara.
"""

from urllib.parse import parse_qs, urlparse

from django.db import migrations

CHUNK = 500


def backfill(apps, schema_editor):
	Restaurant = apps.get_model("restaurants", "Restaurant")
	pending = []
	queryset = Restaurant.objects.exclude(image_url="").filter(photo_ref="")

	for restaurant in queryset.only("id", "image_url", "photo_ref").iterator(chunk_size=CHUNK):
		refs = parse_qs(urlparse(restaurant.image_url).query).get("ref") or []
		ref = (refs[0] if refs else "").strip()
		if not ref.startswith("places/"):
			continue
		restaurant.photo_ref = ref[:1000]
		pending.append(restaurant)
		if len(pending) >= CHUNK:
			Restaurant.objects.bulk_update(pending, ["photo_ref"])
			pending = []

	if pending:
		Restaurant.objects.bulk_update(pending, ["photo_ref"])


class Migration(migrations.Migration):
	dependencies = [("restaurants", "0014_restaurant_photo_ref")]

	operations = [
		# Sin reverse: revertir es borrar la columna, que hace la 0014.
		migrations.RunPython(backfill, migrations.RunPython.noop),
	]
