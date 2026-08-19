"""Reescribe `image_url` para que apunte al lugar y no a la foto, y borra `photo_ref`.

Los photo refs de Google caducan. Las URLs guardadas los llevaban en el query
string, así que cuando vencieron todas las fotos del catálogo empezaron a dar
`400 INVALID_ARGUMENT: The photo resource in the request is invalid` — un
`?ref=` muerto no se recupera solo. El place_id no caduca, y el ref vigente se
saca del details cacheado en el momento de servir la foto.

Sin este backfill los restaurantes ya importados quedarían con URLs que no
sirven hasta que alguien los reimportara uno por uno.
"""

from urllib.parse import urlparse

from django.db import migrations

CHUNK = 500


def rewrite_urls(apps, schema_editor):
	Restaurant = apps.get_model("restaurants", "Restaurant")
	pending = []
	queryset = Restaurant.objects.exclude(image_url="").exclude(google_place_id=None)

	for restaurant in queryset.only("id", "image_url", "google_place_id").iterator(
		chunk_size=CHUNK
	):
		parsed = urlparse(restaurant.image_url)
		# Sólo las URLs de nuestro propio proxy: si alguien cargó una imagen
		# externa a mano, se deja como está.
		if not parsed.path.endswith("/places/photo/"):
			continue
		base = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
		restaurant.image_url = f"{base}?place={restaurant.google_place_id}"[:2000]
		pending.append(restaurant)
		if len(pending) >= CHUNK:
			Restaurant.objects.bulk_update(pending, ["image_url"])
			pending = []

	if pending:
		Restaurant.objects.bulk_update(pending, ["image_url"])


class Migration(migrations.Migration):
	dependencies = [("restaurants", "0015_backfill_photo_ref")]

	operations = [
		# Primero reescribir, después borrar la columna: el orden importa sólo
		# por claridad —el backfill no la usa—, pero deja la migración legible.
		migrations.RunPython(rewrite_urls, migrations.RunPython.noop),
		migrations.RemoveField(model_name="restaurant", name="photo_ref"),
	]
