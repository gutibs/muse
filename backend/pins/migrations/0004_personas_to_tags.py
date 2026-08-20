"""Pasa las personas de cada pin al eje `occasion` de Tag.

En producción esto no mueve una sola fila —no hay personas cargadas, y
ninguno de los 211 pins tiene una— pero sí en cualquier base local levantada
con `make seed`. Corre igual en las dos para que el estado del código sea el
mismo en todas partes.

El emparejamiento es por slug, que es lo único que compartían los dos
modelos. Una persona sin tag equivalente se registra en el log y no se
pierde en silencio: se convierte en un tag de ocasión nuevo.
"""

import logging

from django.db import migrations

logger = logging.getLogger(__name__)


def forwards(apps, schema_editor):
	Persona = apps.get_model("pins", "Persona")
	Pin = apps.get_model("pins", "Pin")
	Tag = apps.get_model("restaurants", "Tag")

	if not Persona.objects.exists():
		return

	equivalencias = {}
	for persona in Persona.objects.all():
		tag = Tag.objects.filter(slug=persona.slug).first()
		if tag is None:
			tag = Tag.objects.create(name=persona.name, slug=persona.slug, kind="occasion")
			logger.info("Persona sin equivalente, creada como tag: %s", persona.slug)
		equivalencias[persona.id] = tag

	for pin in Pin.objects.prefetch_related("personas").iterator():
		tags = [equivalencias[p.id] for p in pin.personas.all()]
		if tags:
			pin.tags.add(*tags)


def backwards(apps, schema_editor):
	"""Devuelve los tags de ocasión a personas, por slug.

	Sólo puede recuperar lo que tenga una persona con el mismo slug; un tag de
	ocasión creado después de la migración no tiene a dónde volver.
	"""
	Persona = apps.get_model("pins", "Persona")
	Pin = apps.get_model("pins", "Pin")

	por_slug = {p.slug: p for p in Persona.objects.all()}
	for pin in Pin.objects.prefetch_related("tags").iterator():
		personas = [por_slug[t.slug] for t in pin.tags.all() if t.slug in por_slug]
		if personas:
			pin.personas.add(*personas)


class Migration(migrations.Migration):
	dependencies = [("pins", "0003_pin_tags")]

	operations = [migrations.RunPython(forwards, backwards)]
