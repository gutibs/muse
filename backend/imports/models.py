"""El registro de un import, que es también su cola.

Mismo patrón que `NotificationJob`: la cola vive en Postgres y la despacha un
management command desde el cron. **No en Redis**, por lo mismo que allá — el
desplegado corre con `--save ""` y `allkeys-lru`, así que pierde trabajos en un
restart y por desalojo.

**El archivo no se guarda.** Se parsea al subir y lo que queda son las filas en
`report`: nombres de restaurantes que la persona ya nos está confiando, y nada
más. Guardar el archivo original sería sumar un dato personal que no necesitamos
para nada.
"""

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class ImportJob(models.Model):
	class State(models.TextChoices):
		PENDING = "pending", "Pending"
		"""Parseado. Espera que el cron lo matchee."""
		PROCESSING = "processing", "Processing"
		READY = "ready", "Ready"
		"""Matcheado. Espera que la persona confirme."""
		CONFIRMED = "confirmed", "Confirmed"
		FAILED = "failed", "Failed"

	user = models.ForeignKey(
		settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="import_jobs"
	)
	source = models.CharField(max_length=255, blank=True, help_text=_("Original file name"))
	state = models.CharField(
		max_length=12, choices=State.choices, default=State.PENDING, db_index=True
	)

	total = models.PositiveIntegerField(default=0)
	processed = models.PositiveIntegerField(default=0)
	matched = models.PositiveIntegerField(default=0)
	failed = models.PositiveIntegerField(default=0)

	# Una entrada por fila: `{row, name, city, outcome, restaurant_id, detail}`.
	# Es lo que la pantalla de confirmación le muestra a la persona antes de
	# crear un solo pin.
	report = models.JSONField(default=list, blank=True)

	# Igual que en la cola de notificaciones: un proceso que se muere a mitad
	# deja el job en `processing` para siempre si no hay con qué detectarlo.
	locked_at = models.DateTimeField(null=True, blank=True)
	LOCK_TIMEOUT_MINUTES = 15

	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		ordering = ["-created_at"]

	def __str__(self) -> str:
		return f"import #{self.pk} de {self.user_id}: {self.state} ({self.matched}/{self.total})"
