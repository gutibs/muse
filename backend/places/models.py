"""Caché persistente de las respuestas de Google Places.

Vive en Postgres y no en Redis a propósito. El deploy hace `down` + `up -d`,
y Redis corre sin persistencia y con `allkeys-lru`, así que una entrada ahí
no sobrevive a un push ni a la presión de memoria. El TTL de 30 días no es
una elección de performance: los Google Maps Platform Terms permiten cachear
los Place IDs indefinidamente pero el resto del contenido hasta 30 días, y
una caché que se vacía sola cada vez que desplegamos nunca aprovecha esa
ventana — le volvemos a pagar a Google por datos que ya teníamos.
"""

from django.db import models


class PlaceDetailsCache(models.Model):
	"""Una respuesta de Places Details, por `(place_id, field_mask)`.

	El `field_mask` es parte de la clave porque la respuesta sólo trae los
	campos que se pidieron: servir un payload guardado con un mask más chico
	daría un restaurante a medio importar, sin ningún error que lo delate.
	"""

	place_id = models.CharField(max_length=255)
	field_mask = models.CharField(max_length=1000)
	payload = models.JSONField()
	fetched_at = models.DateTimeField()

	class Meta:
		constraints = [
			models.UniqueConstraint(
				fields=["place_id", "field_mask"],
				name="uniq_place_details_cache_key",
			)
		]
		# El purge barre por fecha sobre la tabla entera.
		indexes = [models.Index(fields=["fetched_at"], name="place_details_fetched_idx")]

	def __str__(self):
		return f"{self.place_id} ({self.fetched_at:%Y-%m-%d})"
