"""Siembra los tres ejes de la taxonomía.

Por migración y no por fixture: `make seed` no corre en producción, y por eso
ahí había cuatro tags mientras `fixtures/tags.json` declaraba doce. Un eje
sembrado por fixture es un eje vacío para todos los usuarios reales.

Idempotente por slug. Los doce tags que ya existían se reclasifican en su eje
—mezclaban vibe y scene sin distinguirlos— y las doce ocasiones, que hasta
ahora eran el modelo `Persona` de la app `pins`, se crean acá.
"""

from django.db import migrations

VIBE = [
	("Quiet", "quiet"),
	("Romantic", "romantic"),
	("Trendy", "trendy"),
	("Classic", "classic"),
	("Casual", "casual"),
	("Fine Dining", "fine-dining"),
	("Good Vibes", "good-vibes"),
]

SCENE = [
	("Outdoor / Terrace", "outdoor-terrace"),
	("Live Music", "live-music"),
	("Pet Friendly", "pet-friendly"),
	("Family Friendly", "family-friendly"),
	("Instagrammable", "instagrammable"),
]

OCCASION = [
	("Date Night", "date-night"),
	("Family Dinner", "family-dinner"),
	("Girls Night", "girls-night"),
	("Business Lunch", "business-lunch"),
	("Mums & Babies", "mums-babies"),
	("Special Occasion", "special-occasion"),
	("Quick Bite", "quick-bite"),
	("Brunch", "brunch"),
	("Drinks & Bar", "drinks-bar"),
	("Foodie Experience", "foodie-experience"),
	("Group Gathering", "group-gathering"),
	("Solo Dining", "solo-dining"),
]


def seed(apps, schema_editor):
	Tag = apps.get_model("restaurants", "Tag")

	for kind, entries in (("vibe", VIBE), ("scene", SCENE), ("occasion", OCCASION)):
		for name, slug in entries:
			tag, created = Tag.objects.get_or_create(
				slug=slug, defaults={"name": name, "kind": kind}
			)
			if not created and tag.kind != kind:
				# Existía con el kind por defecto (`general`), porque el
				# fixture no lo declaraba. Se reclasifica sin tocar el nombre,
				# que puede haber sido editado desde el admin.
				tag.kind = kind
				tag.save(update_fields=["kind"])


def unseed(apps, schema_editor):
	"""Vuelve los ejes a `general` en vez de borrar.

	Borrar se llevaría por delante las relaciones con pins y restaurantes que
	ya existieran, y una marcha atrás de esquema no debería destruir datos de
	usuario.
	"""
	Tag = apps.get_model("restaurants", "Tag")
	slugs = [slug for _, slug in VIBE + SCENE + OCCASION]
	Tag.objects.filter(slug__in=slugs).update(kind="general")


class Migration(migrations.Migration):
	dependencies = [("restaurants", "0019_alter_tag_kind")]

	operations = [migrations.RunPython(seed, unseed)]
