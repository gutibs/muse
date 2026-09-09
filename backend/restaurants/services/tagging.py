"""Traduce texto libre a etiquetas del catálogo.

Único punto donde lo que alguien escribió en un archivo se convierte en filas
de `Tag`. Los slugs son únicos en toda la tabla, así que no hace falta saber de
qué eje viene cada uno: alcanza con el texto.
"""

import logging

from restaurants.models import Restaurant, Tag

logger = logging.getLogger(__name__)


def apply_tags(restaurant: Restaurant, textos: list[str]) -> tuple[list[str], list[str]]:
	"""Agrega al restaurante las etiquetas que existan. Devuelve `(aplicadas, desconocidas)`."""
	if not textos:
		return [], []

	encontradas = {tag.slug: tag for tag in Tag.objects.filter(slug__in=textos)}
	aplicadas = [texto for texto in textos if texto in encontradas]
	desconocidas = [texto for texto in textos if texto not in encontradas]

	if aplicadas:
		restaurant.tags.add(*[encontradas[slug] for slug in aplicadas])

	return aplicadas, desconocidas
