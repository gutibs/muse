import uuid

from django.conf import settings
from django.contrib.gis.db import models as gis_models
from django.db import models


class DietaryPreference(models.Model):
	"""Closed set of dietary preferences a user can have. Replaces the
	previous comma-separated CharField on Profile (see migration 0005);
	enables proper FK validation + future joins (e.g. "find friends with
	the same preferences").

	Rows are seeded by migration; not user-creatable from the app.
	"""

	name = models.CharField(max_length=40, unique=True)
	slug = models.SlugField(max_length=40, unique=True)

	class Meta:
		db_table = "accounts_dietary_preference"
		ordering = ["name"]

	def __str__(self):
		return self.name


class Profile(models.Model):
	user = models.OneToOneField(
		settings.AUTH_USER_MODEL,
		on_delete=models.CASCADE,
		related_name="profile",
	)
	display_name = models.CharField(max_length=100, blank=True)
	bio = models.CharField(max_length=300, blank=True)
	avatar = models.ImageField(upload_to="avatars/", blank=True)
	city = models.CharField(max_length=100, blank=True)
	location = gis_models.PointField(null=True, blank=True, srid=4326)
	website = models.URLField(blank=True)
	instagram = models.CharField(max_length=60, blank=True)
	phone = models.CharField(max_length=20, blank=True)
	favourite_cuisine = models.ForeignKey(
		"restaurants.Cuisine",
		on_delete=models.SET_NULL,
		null=True,
		blank=True,
		related_name="+",
	)
	dietary_preferences = models.ManyToManyField(
		DietaryPreference,
		blank=True,
		related_name="profiles",
	)
	# Derecho de oposición (art. 21 GDPR). Con esto en True no se registra
	# ningún evento de analytics de esta persona — ni los que manda la app ni
	# los que emite el servidor. Lo prometen las políticas publicadas, así que
	# tiene que ser verdad en el código.
	analytics_opt_out = models.BooleanField(default=False)
	# Set when the user exercises their right to erasure. The row stays so the
	# person's reviews keep hanging off a valid FK (see D-009), but everything
	# identifying is wiped. Anything rendering an author must treat a non-null
	# value as "anonymous" — the label itself is the client's job, translated.
	deleted_at = models.DateTimeField(null=True, blank=True)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		db_table = "accounts_profile"

	def __str__(self):
		if self.deleted_at:
			return "Deleted user"
		return self.display_name or self.user.email or self.user.username


class ConsentRecord(models.Model):
	"""Proof that a user actively consented to a data-protection policy at a
	given point in time. One row per (user, policy) acceptance. GDPR/PDPO
	require being able to demonstrate *when* and *to which version* consent
	was given — hence policy_version + accepted_at + ip_address.

	Append-only by intent: re-consenting to a new policy version creates a new
	row, it does not overwrite the old one. Never edited from the admin.
	"""

	class Policy(models.TextChoices):
		GDPR = "gdpr", "GDPR"
		PDPO = "pdpo", "PDPO"

	user = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.CASCADE,
		related_name="consents",
	)
	policy = models.CharField(max_length=10, choices=Policy.choices)
	policy_version = models.CharField(max_length=20)
	accepted_at = models.DateTimeField(auto_now_add=True)
	ip_address = models.GenericIPAddressField(null=True, blank=True)

	class Meta:
		db_table = "accounts_consent_record"
		ordering = ["-accepted_at"]
		indexes = [models.Index(fields=["user", "policy"], name="accounts_co_user_id_idx")]

	def __str__(self):
		return f"{self.user} accepted {self.policy} v{self.policy_version}"


class Friendship(models.Model):
	class Status(models.TextChoices):
		PENDING = "pending", "Pending"
		ACCEPTED = "accepted", "Accepted"
		DECLINED = "declined", "Declined"

	from_user = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.CASCADE,
		related_name="friendships_sent",
	)
	to_user = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.CASCADE,
		related_name="friendships_received",
	)
	status = models.CharField(
		max_length=10,
		choices=Status.choices,
		default=Status.PENDING,
	)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		db_table = "accounts_friendship"
		unique_together = ("from_user", "to_user")
		ordering = ["-created_at"]

	def __str__(self):
		return f"{self.from_user} → {self.to_user} ({self.status})"


class EmailInvitation(models.Model):
	from_user = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.CASCADE,
		related_name="invitations_sent",
	)
	email = models.EmailField()
	token = models.UUIDField(default=uuid.uuid4, unique=True)
	accepted = models.BooleanField(default=False)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		db_table = "accounts_email_invitation"
		unique_together = ("from_user", "email")

	def __str__(self):
		return f"{self.from_user} invited {self.email}"


class PasswordResetCode(models.Model):
	"""Un código de recuperación de contraseña, de un solo uso.

	Es una credencial, así que se guarda hasheada con el mismo mecanismo que
	una contraseña (RF11) — nunca en claro, ni en la fila ni en los logs. Se
	descartó reusar el patrón de EmailInvitation, que persiste un UUID legible
	y no expira: ahí el token no protege nada y acá sí.

	`attempts` es lo que hace que seis dígitos alcancen; se incrementa siempre
	con un UPDATE atómico (ver services/password_reset.py), nunca leyendo y
	escribiendo desde Python.
	"""

	CODE_DIGITS = 6
	MAX_ATTEMPTS = 5
	TTL_MINUTES = 15
	# RF4: tope de códigos por casilla destino y ventana en la que se cuenta.
	MAX_PER_WINDOW = 3
	WINDOW_HOURS = 1

	user = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.CASCADE,
		related_name="password_reset_codes",
	)
	code_hash = models.CharField(max_length=128)
	expires_at = models.DateTimeField()
	attempts = models.PositiveSmallIntegerField(default=0)
	used_at = models.DateTimeField(null=True, blank=True)
	# RF5: null cuando Resend falló. La fila queda para poder reenviar a mano;
	# el usuario recibe la misma respuesta que si hubiera salido (RF2).
	sent_at = models.DateTimeField(null=True, blank=True)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		db_table = "accounts_password_reset_code"
		ordering = ["-created_at"]
		indexes = [
			models.Index(fields=["user", "-created_at"], name="accounts_prc_user_idx"),
		]

	def __str__(self):
		return f"Reset code for {self.user_id} (expires {self.expires_at:%Y-%m-%d %H:%M})"


class Block(models.Model):
	"""Una persona decidió dejar de ver a otra, y de ser vista por ella.

	La fila es **direccional** —guarda quién bloqueó a quién, que es lo que hace
	falta para poder desbloquear— pero el efecto en visibilidad es **simétrico**:
	ninguna superficie mira la dirección, todas preguntan por
	`accounts.services.visibility.blocked_user_ids`, que junta las dos.

	No se reusó `Friendship.DECLINED`: hoy no filtra nada, el emisor puede
	borrar la fila y volver a solicitar, y su `unique_together` es direccional
	por otra razón.

	El bloqueo es silencioso (RF2): al bloqueado no se le dice nada, ni por
	respuesta ni por ausencia de respuesta. Cualquier endpoint que devuelva el
	estado de bloqueo tiene que hacerlo sólo para quien bloqueó.
	"""

	blocker = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.CASCADE,
		related_name="blocks_made",
	)
	blocked = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.CASCADE,
		related_name="blocks_received",
	)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		db_table = "accounts_block"
		unique_together = ("blocker", "blocked")
		ordering = ["-created_at"]
		indexes = [
			models.Index(fields=["blocked"], name="accounts_block_blocked_idx"),
		]

	def __str__(self):
		return f"{self.blocker_id} blocked {self.blocked_id}"
