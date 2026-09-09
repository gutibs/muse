"""Caché persistente de las respuestas de Google Places.

Vive en Postgres y no en Redis a propósito. El deploy hace `down` + `up -d`,
y Redis corre sin persistencia y con `allkeys-lru`, así que una entrada ahí
no sobrevive a un push ni a la presión de memoria. El TTL de 30 días no es
una elección de performance: los Google Maps Platform Terms permiten cachear
los Place IDs indefinidamente pero el resto del contenido hasta 30 días, y
una caché que se vacía sola cada vez que desplegamos nunca aprovecha esa
ventana — le volvemos a pagar a Google por datos que ya teníamos.

Y el estado de salud de la integración, que no es caché pero vive acá por la
misma razón: tiene que sobrevivir al `down` + `up -d` del deploy para que un
corte no se avise dos veces.
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


class PlacePhoto(models.Model):
	"""Los bytes de una foto de Places, guardados en nuestro propio storage.

	La clave es `(place_id, width)` y **no** el nombre de recurso de la foto:
	los photo refs de Google caducan. Los que estaban guardados desde el import
	devolvían `400 INVALID_ARGUMENT: The photo resource in the request is
	invalid` (verificado contra la API el 2026-08-19), así que una clave basada
	en el ref apunta a algo que deja de existir. El place_id no caduca.

	`photo_ref` queda como registro de con qué ref se bajaron estos bytes —sirve
	para diagnosticar—, nunca como clave ni como algo a reusar.
	"""

	place_id = models.CharField(max_length=255)
	width = models.PositiveIntegerField()
	photo_ref = models.CharField(max_length=1000, blank=True)
	file = models.ImageField(upload_to="place-photos/")
	# authorAttributions del payload de details. Los Google Maps Platform Terms
	# exigen mostrar el autor de la foto junto con la foto.
	attribution = models.JSONField(default=list, blank=True)
	fetched_at = models.DateTimeField()

	class Meta:
		constraints = [
			models.UniqueConstraint(
				fields=["place_id", "width"],
				name="uniq_place_photo_key",
			)
		]
		indexes = [models.Index(fields=["fetched_at"], name="place_photo_fetched_idx")]

	def __str__(self):
		return f"{self.place_id} @{self.width}px"


class IntegrationHealth(models.Model):
	"""Lo que sabemos de un servicio externo, entre una corrida del chequeo y la siguiente.

	Existe por un caso real: el 2026-09-08 la cuenta de billing de Google
	quedó cerrada, Places dejó de responder por tiempo indeterminado y nadie se
	enteró — se descubrió de casualidad corriendo la suite antes de un merge.
	Con 57 restaurantes en el catálogo, agregar restaurantes es el flujo
	principal de la app, así que el corte se llevó lo que la gente viene a hacer.

	Una fila por servicio. `service` es la clave para que sumar Resend o FCM
	después sea una fila más y no un modelo nuevo.

	`alerted` está separado de `is_healthy` a propósito: son dos hechos
	distintos —qué pasa y si ya avisamos— y confundirlos pierde avisos. Si
	Resend falla justo cuando hay que mandar la alerta, la fila queda en
	"caído, sin avisar" y la corrida siguiente reintenta; con un solo campo, el
	cambio de estado ya estaría consumido y el corte se avisaría nunca.
	"""

	service = models.CharField(max_length=50, unique=True)
	is_healthy = models.BooleanField(default=True)
	# Cuándo se corrió el chequeo por última vez, haya cambiado algo o no.
	checked_at = models.DateTimeField()
	# Cuándo pasó a ser lo que es hoy. La resta contra `now` es la duración del
	# corte que va en el mail de recuperación.
	changed_at = models.DateTimeField()
	last_error = models.TextField(blank=True)
	alerted = models.BooleanField(default=False)
	# Cuánto duró el último corte, calculado al detectar la recuperación y
	# guardado acá. No se deriva al mandar el mail: para entonces `changed_at`
	# ya es el momento de la recuperación y la duración se perdió. Sin esto, un
	# aviso de recuperación reintentado —porque el primero falló— sale diciendo
	# "Downtime: unknown", que es justo el único dato que ese mail lleva.
	last_downtime = models.DurationField(null=True, blank=True)

	class Meta:
		verbose_name_plural = "integration health"

	def __str__(self):
		return f"{self.service}: {'ok' if self.is_healthy else 'down'}"
