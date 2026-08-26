"""Recuperación de contraseña por código de 6 dígitos.

Punto único de escritura y de canje de PasswordResetCode. Ver
docs/SPEC_RESET_PASSWORD.md — las decisiones que parecen raras leyendo el
código suelto (responder igual cuando la cuenta no existe, hashear al pedo,
incrementar el contador antes de comparar) están ahí justificadas.

El código en claro existe sólo dentro de `issue_code` y del email. No se
persiste, no se loguea y no se devuelve por HTTP.
"""

import logging
import secrets
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import check_password, make_password
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.db.models import F
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from accounts.models import PasswordResetCode
from accounts.services.email import EmailSendError, send_password_reset_email

logger = logging.getLogger(__name__)

User = get_user_model()

# Mensaje único para todo fallo de canje: código errado, vencido, quemado,
# ya usado o inexistente. Distinguirlos le diría al atacante en cuál de esos
# estados está, que es justo lo que no queremos que sepa.
_INVALID = "Invalid or expired code."


def _find_active_user(email: str):
	"""La cuenta anonimizada (is_active=False) se trata como inexistente: no
	recibe código ni email. Ver §6 de la spec."""
	if not email:
		return None
	return User.objects.filter(email__iexact=email.strip(), is_active=True).first()


def _burn_equivalent_hash() -> None:
	"""RF3. Hashear es lo más caro del request; si el camino sin cuenta se lo
	saltea, la diferencia de tiempo entre los dos caminos dice quién tiene
	cuenta. No cierra el canal entero —el camino con cuenta además habla con
	Resend— pero sí la parte grande y medible. La limitación que queda está
	declarada en §4 de la spec."""
	make_password(_random_code())


def _cooldown_exceeded(user) -> bool:
	"""RF4: tope por casilla destino. El throttle por IP no impide inundar el
	buzón de otra persona con mails que salen de nuestro dominio, ni frena a
	quien pide códigos en serie para probar un valor fijo contra cada uno.
	El destino es siempre el email del usuario, así que contar por usuario es
	contar por casilla."""
	window_start = timezone.now() - timedelta(hours=PasswordResetCode.WINDOW_HOURS)
	recent = PasswordResetCode.objects.filter(user=user, created_at__gte=window_start).count()
	return recent >= PasswordResetCode.MAX_PER_WINDOW


def _random_code() -> str:
	return f"{secrets.randbelow(10 ** PasswordResetCode.CODE_DIGITS):0{PasswordResetCode.CODE_DIGITS}d}"


def issue_code(user) -> str:
	"""Crea un código nuevo para `user` y devuelve su valor en claro.

	RF9: vence cualquier código anterior que siguiera vivo, en la misma
	transacción. No los borra —de eso se encarga la limpieza (RF17)—: vencerlos
	dice lo que de verdad pasó, que nadie los usó. Si sobrevivieran vigentes,
	quemar los cinco intentos del nuevo devolvería la búsqueda al viejo y el
	tope de intentos valdría el doble.
	"""
	code = _random_code()
	now = timezone.now()
	with transaction.atomic():
		PasswordResetCode.objects.filter(
			user=user, used_at__isnull=True, expires_at__gt=now
		).update(expires_at=now)
		PasswordResetCode.objects.create(
			user=user,
			code_hash=make_password(code),
			expires_at=now + timedelta(minutes=PasswordResetCode.TTL_MINUTES),
		)
	return code


def request_reset(*, email: str, language: str | None = None) -> None:
	"""RF1-RF5. No devuelve nada y no levanta nada: la vista responde lo
	mismo pase lo que pase acá (RF2), y cualquier diferencia observable —un
	status, un cuerpo, una excepción que se escape— es un oráculo de
	enumeración."""
	user = _find_active_user(email)
	if user is None:
		_burn_equivalent_hash()
		logger.info("Password reset requested for unknown or inactive email")
		return

	if _cooldown_exceeded(user):
		logger.warning("Password reset cooldown hit", extra={"user_id": user.id})
		return

	code = issue_code(user)
	entry = PasswordResetCode.objects.filter(user=user).order_by("-created_at").first()
	try:
		send_password_reset_email(to_email=user.email, code=code, language=language)
	except EmailSendError as exc:
		# RF5: la fila queda con sent_at en null, que es lo que hay que mirar
		# para reenviar a mano. El usuario recibe lo mismo que si hubiera
		# salido (RF2): que el fallo se note sería un oráculo de enumeración,
		# porque sólo puede pasarle a un email que existe.
		logger.error(
			"Password reset email not sent (status=%s): %s",
			exc.status_code,
			exc.message,
			extra={"user_id": user.id, "reset_code_id": entry.id if entry else None},
		)
		return

	if entry is not None:
		entry.sent_at = timezone.now()
		entry.save(update_fields=["sent_at"])
	logger.info("Password reset code sent", extra={"user_id": user.id})


def confirm_reset(*, email: str, code: str, new_password: str):
	"""RF6-RF13. Devuelve el usuario con la contraseña ya cambiada.

	Levanta ValidationError de DRF (→ 400) en cualquier fallo de canje, y con
	el mismo mensaje para todos.
	"""
	user = _find_active_user(email)
	if user is None:
		# Mismo costo y mismo error que un código errado.
		_burn_equivalent_hash()
		raise ValidationError({"code": [_INVALID]})

	# RF6: por usuario primero, nunca por código. Si dos personas tienen el
	# mismo código vivo, cada una alcanza sólo el suyo.
	entry = (
		PasswordResetCode.objects.filter(user=user, used_at__isnull=True)
		.order_by("-created_at")
		.first()
	)
	if entry is None:
		raise ValidationError({"code": [_INVALID]})

	# RF8: el intento se cobra en la base, con un UPDATE condicional. Que sea
	# una sola sentencia es lo que hace que cinco requests simultáneas cuenten
	# cinco y no una. Si no actualizó ninguna fila, el código ya estaba quemado
	# o usado.
	charged = PasswordResetCode.objects.filter(
		pk=entry.pk,
		used_at__isnull=True,
		attempts__lt=PasswordResetCode.MAX_ATTEMPTS,
	).update(attempts=F("attempts") + 1)
	if not charged:
		logger.warning("Password reset attempt on burned code", extra={"user_id": user.id})
		raise ValidationError({"code": [_INVALID]})

	entry.refresh_from_db()

	# RF7: se compara contra expires_at al momento del canje, en UTC.
	if entry.expires_at <= timezone.now():
		logger.info("Password reset attempt on expired code", extra={"user_id": user.id})
		raise ValidationError({"code": [_INVALID]})

	if not check_password(code or "", entry.code_hash):
		logger.info(
			"Password reset attempt with wrong code",
			extra={"user_id": user.id, "attempts": entry.attempts},
		)
		raise ValidationError({"code": [_INVALID]})

	# RF12: las mismas validaciones que aplica el registro. Va después de
	# validar el código, para no convertir esto en un validador de contraseñas
	# abierto a cualquiera que pase por acá.
	try:
		validate_password(new_password, user=user)
	except DjangoValidationError as exc:
		raise ValidationError({"new_password": list(exc.messages)}) from exc

	with transaction.atomic():
		# RF10: el código se consume acá, en la misma transacción que el
		# cambio de contraseña.
		used = PasswordResetCode.objects.filter(pk=entry.pk, used_at__isnull=True).update(
			used_at=timezone.now()
		)
		if not used:
			raise ValidationError({"code": [_INVALID]})
		user.set_password(new_password)
		user.save(update_fields=["password"])

	# RF13: el hash de la contraseña cambió, así que los tokens firmados con
	# el hash anterior dejan de validar (CHECK_REVOKE_TOKEN).
	logger.info("Password reset completed", extra={"user_id": user.id})
	return user
