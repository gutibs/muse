"""El marcador de datos sembrados pasa de tag a booleano.

Como tag, `demo` ocupaba una fila en la misma tabla que los ejes de la
taxonomía: salía en el endpoint público de tags —`TagViewSet` sin `?kind`
devuelve la tabla entera— y viajaba en el `tags_detail` de cada restaurante
sembrado. Como booleano indexado se identifica y se borra sin join, y la tabla
de tags queda sólo con lo que describe lugares de verdad.
"""

from django.db import migrations, models

SLUG = "demo"


def tag_a_flag(apps, schema_editor):
	Restaurant = apps.get_model("restaurants", "Restaurant")
	Tag = apps.get_model("restaurants", "Tag")

	tag = Tag.objects.filter(slug=SLUG).first()
	if tag is None:
		return

	# `update` y no un loop: son ~500 filas en producción y no hay señales de
	# save que necesiten dispararse.
	Restaurant.objects.filter(tags=tag).update(is_demo=True)
	tag.delete()


def flag_a_tag(apps, schema_editor):
	Restaurant = apps.get_model("restaurants", "Restaurant")
	Tag = apps.get_model("restaurants", "Tag")

	marcados = Restaurant.objects.filter(is_demo=True)
	if not marcados.exists():
		return

	tag, _ = Tag.objects.get_or_create(
		slug=SLUG, defaults={"name": "Demo", "kind": "general"}
	)
	for restaurant in marcados:
		restaurant.tags.add(tag)


class Migration(migrations.Migration):
	dependencies = [("restaurants", "0022_restaurant_is_closed")]

	operations = [
		migrations.AddField(
			model_name="restaurant",
			name="is_demo",
			field=models.BooleanField(db_index=True, default=False),
		),
		migrations.RunPython(tag_a_flag, flag_a_tag),
	]
