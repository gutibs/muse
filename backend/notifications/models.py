"""Push notifications: dispositivos, cola de envíos y marca del resumen diario.

Dos canales, deliberadamente distintos (ver `docs/SPEC_F2E_PUSH.md`):

- **Inmediato**, para lo dirigido a una persona —te llegó una solicitud, te la
  aceptaron—. Pasa por `NotificationJob`, que es la cola.
- **Resumen diario**, para la actividad de los amigos. NO pasa por la cola: se
  arma en el momento de mandarlo, porque guardarlo antes sería guardar una foto
  que puede quedar vieja. Un pin que pasó a privado entre el armado y el envío
  se filtraría igual, que es exactamente el oráculo que F2.A cerró.

La cola vive en Postgres y no en Redis a propósito: el Redis desplegado corre
con `--save ""` y `--maxmemory-policy allkeys-lru`, así que pierde trabajos en
un reinicio y puede perderlos por desalojo. Sirve como caché, que es para lo
que se eligió.
"""

from django.conf import settings
from django.db import models


class DeviceToken(models.Model):
	"""Un dispositivo al que se le puede mandar push.

	`token` es único a nivel tabla y no por usuario: el mismo teléfono con dos
	cuentas tiene un solo token de FCM, así que registrar con la segunda cuenta
	tiene que mover la fila, no duplicarla. Si no, la primera cuenta seguiría
	recibiendo notificaciones en un teléfono que ya no es suyo.
	"""

	# Tope por persona. Sin esto, el teléfono que cambiaste el año pasado y
	# nunca deslogueaste sigue registrado y sigue recibiendo.
	MAX_PER_USER = 5
	# Un token que no se ve hace este tiempo se borra desde el cron.
	STALE_DAYS = 90

	class Platform(models.TextChoices):
		ANDROID = "android", "Android"
		IOS = "ios", "iOS"

	user = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.CASCADE,
		related_name="device_tokens",
	)
	token = models.CharField(max_length=255, unique=True)
	platform = models.CharField(
		max_length=10,
		choices=Platform.choices,
		default=Platform.ANDROID,
	)
	last_seen_at = models.DateTimeField(auto_now=True)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ("-last_seen_at",)
		indexes = [models.Index(fields=["user", "-last_seen_at"])]

	def __str__(self):
		return f"{self.user_id}:{self.platform}:{self.token[:12]}…"


class NotificationJob(models.Model):
	"""Un envío pendiente del canal inmediato.

	Se escribe con `transaction.on_commit()` desde los signals y lo despacha
	`dispatch_notifications`. Ningún envío a FCM ocurre dentro de un request:
	el antecedente que no hay que repetir es el email de invitación, que se
	manda inline y bloquea la respuesta.
	"""

	# Un job tomado por un proceso que murió vuelve a la cola pasado esto. El
	# deploy hace `down` + `up` en cada push, así que un worker cortado a mitad
	# de lote es un escenario semanal, no teórico.
	LOCK_TIMEOUT_MINUTES = 10
	MAX_ATTEMPTS = 3
	# Más viejo que esto se descarta en vez de entregarse: si el despachador
	# estuvo caído, nadie quiere que le avisen ahora de una solicitud de ayer.
	STALE_HOURS = 6
	# Un job terminado se borra pasado esto, desde el cron de mantenimiento.
	KEEP_DAYS = 7

	class Kind(models.TextChoices):
		FRIENDSHIP_REQUEST = "friendship_request", "Friend request received"
		FRIENDSHIP_ACCEPTED = "friendship_accepted", "Friend request accepted"

	class State(models.TextChoices):
		PENDING = "pending", "Pending"
		PROCESSING = "processing", "Processing"
		SENT = "sent", "Sent"
		FAILED = "failed", "Failed"
		DISCARDED = "discarded", "Discarded"

	recipient = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.CASCADE,
		related_name="notification_jobs",
	)
	actor = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.CASCADE,
		null=True,
		blank=True,
		related_name="+",
	)
	kind = models.CharField(max_length=32, choices=Kind.choices)
	state = models.CharField(max_length=12, choices=State.choices, default=State.PENDING)
	# Identifica el evento, no la fila. Con índice único, restaurar un backup
	# —el deploy hace `pg_dump` antes de cada corrida— no puede volver a mandar
	# lo que ya se entregó.
	idempotency_key = models.CharField(max_length=200, unique=True)
	context = models.JSONField(default=dict, blank=True)
	attempts = models.PositiveSmallIntegerField(default=0)
	locked_at = models.DateTimeField(null=True, blank=True)
	last_error = models.TextField(blank=True)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		ordering = ("created_at",)
		indexes = [
			models.Index(fields=["state", "created_at"]),
			models.Index(fields=["state", "locked_at"]),
		]

	def __str__(self):
		return f"{self.kind} → {self.recipient_id} [{self.state}]"


class DigestLog(models.Model):
	"""Marca de que a alguien ya se le mandó el resumen de un día.

	Es lo que hace idempotente a `send_daily_digests`, que corre cada hora y
	tiene que decidir a quién le toca sin mandar dos veces. La fecha es la
	**local de la persona**, no la del servidor: con usuarios en Hong Kong y el
	servidor en horario de Buenos Aires, el "día" no es el mismo.
	"""

	KEEP_DAYS = 90

	user = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.CASCADE,
		related_name="digest_logs",
	)
	local_date = models.DateField()
	item_count = models.PositiveSmallIntegerField(default=0)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ("-local_date",)
		constraints = [
			models.UniqueConstraint(
				fields=["user", "local_date"], name="one_digest_per_user_per_day"
			)
		]

	def __str__(self):
		return f"digest {self.user_id} {self.local_date} ({self.item_count})"
