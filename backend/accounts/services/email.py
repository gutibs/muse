"""Transactional email — Resend integration.

Single canonical entry point for the product's user-facing emails
(invitations, password reset). Callers must NOT use django.core.mail.send_mail
directly anymore.
"""

import logging

import resend
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import escape

logger = logging.getLogger(__name__)

SUPPORTED_LANGUAGES = ("es", "en", "it")
DEFAULT_LANGUAGE = "en"

# Subject lines kept inline (one short string per language) — splitting them
# into their own templates would be more files than the value justifies.
_SUBJECTS = {
	"es": "{inviter_name} te invitó a Muse",
	"en": "{inviter_name} invited you to Muse",
	"it": "{inviter_name} ti ha invitato su Muse",
}

# El código NO va en el asunto: los asuntos aparecen en la preview de la
# notificación del teléfono y en los logs de cualquier intermediario.
_WELCOME_SUBJECTS = {
	"es": "Tu cuenta de Muse está lista",
	"en": "Your Muse account is ready",
	"it": "Il tuo account Muse è pronto",
}

# Deliberadamente neutro: el asunto aparece en la preview del teléfono y no
# tiene por qué anunciarle a quien mire la pantalla que hubo un intento de
# registro con esa dirección.
_ACCOUNT_EXISTS_SUBJECTS = {
	"es": "Sobre tu cuenta de Muse",
	"en": "About your Muse account",
	"it": "Sul tuo account Muse",
}

_RESET_SUBJECTS = {
	"es": "Tu código para recuperar la contraseña",
	"en": "Your password recovery code",
	"it": "Il tuo codice per recuperare la password",
}


class EmailSendError(Exception):
	"""Raised when the email cannot be sent.

	`status_code` is a hint for the HTTP layer:
	- 503: configuration missing (RESEND_API_KEY empty)
	- 502: upstream Resend API call failed
	"""

	def __init__(self, message: str, status_code: int = 500):
		self.message = message
		self.status_code = status_code
		super().__init__(message)


def _normalize_language(language: str | None) -> str:
	if not language:
		return DEFAULT_LANGUAGE
	lang = language.lower()[:2]
	return lang if lang in SUPPORTED_LANGUAGES else DEFAULT_LANGUAGE


def _ensure_configured() -> None:
	if not settings.RESEND_API_KEY:
		raise EmailSendError("RESEND_API_KEY not configured", status_code=503)
	resend.api_key = settings.RESEND_API_KEY


def send_invitation_email(
	*,
	to_email: str,
	inviter_name: str,
	invitation_link: str,
	language: str | None = None,
) -> dict:
	"""Send the invitation email via Resend.

	Returns the Resend response dict on success (contains `id`).
	Raises EmailSendError on configuration or upstream failure.
	"""
	_ensure_configured()
	lang = _normalize_language(language)

	context = {
		"inviter_name": inviter_name,
		"invitation_link": invitation_link,
	}
	html = render_to_string(f"emails/invitation.{lang}.html", context)
	text = render_to_string(f"emails/invitation.{lang}.txt", context)
	subject = _SUBJECTS[lang].format(inviter_name=inviter_name)

	payload = {
		"from": settings.DEFAULT_FROM_EMAIL,
		"to": [to_email],
		"subject": subject,
		"html": html,
		"text": text,
	}

	try:
		response = resend.Emails.send(payload)
	except Exception as exc:
		logger.exception("Resend API call failed for %s", to_email)
		raise EmailSendError(
			f"Failed to send invitation email: {exc}",
			status_code=502,
		) from exc

	logger.info(
		"Invitation email sent",
		extra={
			"to": to_email,
			"resend_id": response.get("id") if isinstance(response, dict) else None,
		},
	)
	return response


def send_password_reset_email(
	*,
	to_email: str,
	code: str,
	language: str | None = None,
) -> dict:
	"""Send the 6-digit password reset code via Resend.

	Returns the Resend response dict on success (contains `id`).
	Raises EmailSendError on configuration or upstream failure — the caller
	decides what to do with it; the HTTP layer must NOT leak it (see RF2 in
	docs/SPEC_RESET_PASSWORD.md: the response is the same whether this works
	or not, or the failure itself tells an attacker the account exists).

	The code is never logged, here or anywhere else (RF11).
	"""
	_ensure_configured()
	lang = _normalize_language(language)

	# Import local: la vigencia la define el modelo y no queremos dos números
	# que puedan divergir, pero tampoco un import de modelos a nivel de módulo
	# en el service de email.
	from accounts.models import PasswordResetCode

	context = {"code": code, "ttl_minutes": PasswordResetCode.TTL_MINUTES}
	html = render_to_string(f"emails/password_reset.{lang}.html", context)
	text = render_to_string(f"emails/password_reset.{lang}.txt", context)

	payload = {
		"from": settings.DEFAULT_FROM_EMAIL,
		"to": [to_email],
		"subject": _RESET_SUBJECTS[lang],
		"html": html,
		"text": text,
	}

	try:
		response = resend.Emails.send(payload)
	except Exception as exc:
		logger.exception("Resend API call failed for password reset to %s", to_email)
		raise EmailSendError(
			f"Failed to send password reset email: {exc}",
			status_code=502,
		) from exc

	logger.info(
		"Password reset email sent",
		extra={
			"to": to_email,
			"resend_id": response.get("id") if isinstance(response, dict) else None,
		},
	)
	return response


def send_report_notification_email(*, report) -> dict:
	"""Avisa al moderador que entró una denuncia.

	Va en inglés y sin template: el destinatario es una sola persona conocida,
	no un usuario del producto, y un template trilingüe para eso sería
	ceremonia sin valor. El cuerpo lleva lo necesario para decidir sin abrir el
	admin, y el id para encontrarlo cuando haga falta.
	"""
	_ensure_configured()

	target = f"pin {report.pin_id}" if report.pin_id else f"user {report.reported_user_id}"
	lines = [
		f"Report #{report.pk} — {report.get_reason_display()}",
		f"Reported: {target}",
		f"Reporter: user {report.reporter_id}",
	]
	if report.detail:
		lines.append(f"Detail: {report.detail}")
	if report.reported_comment:
		lines.append(f"Reported review: {report.reported_comment}")
	body = "\n".join(lines)

	payload = {
		"from": settings.DEFAULT_FROM_EMAIL,
		"to": [settings.MODERATION_EMAIL],
		"subject": f"[Muse] Report #{report.pk}: {report.get_reason_display()}",
		"text": body,
		"html": f"<pre>{escape(body)}</pre>",
	}

	try:
		response = resend.Emails.send(payload)
	except Exception as exc:
		logger.exception("Resend API call failed for report %s", report.pk)
		raise EmailSendError(f"Failed to send report notification: {exc}", status_code=502) from exc

	return response


def _send_account_email(
	*, template: str, subjects: dict, to_email: str, name: str, language
) -> dict:
	"""Los dos mails del alta comparten forma: mismo layout, mismo enlace al
	login, y sólo cambian el asunto y el cuerpo."""
	_ensure_configured()
	lang = _normalize_language(language)
	context = {
		"name_suffix": f" {name}" if name else "",
		"login_link": f"{settings.APP_PUBLIC_URL}/",
	}
	payload = {
		"from": settings.DEFAULT_FROM_EMAIL,
		"to": [to_email],
		"subject": subjects[lang],
		"html": render_to_string(f"emails/{template}.{lang}.html", context),
		"text": render_to_string(f"emails/{template}.{lang}.txt", context),
	}
	try:
		response = resend.Emails.send(payload)
	except Exception as exc:
		logger.exception("Resend API call failed for %s (%s)", to_email, template)
		raise EmailSendError(f"Failed to send {template} email: {exc}", status_code=502) from exc
	return response


def send_welcome_email(*, to_email: str, name: str = "", language=None) -> dict:
	"""Confirma un alta real. No verifica nada: la cuenta ya sirve, y este mail
	es la contraparte visible de que el registro dejó de devolver sesión."""
	return _send_account_email(
		template="welcome",
		subjects=_WELCOME_SUBJECTS,
		to_email=to_email,
		name=name,
		language=language,
	)


def send_account_exists_email(*, to_email: str, language=None) -> dict:
	"""Le avisa al dueño de la casilla que alguien intentó registrarse con su
	email. Es lo que hace que la respuesta del registro pueda ser idéntica en
	los dos casos sin dejar a nadie sin explicación: la explicación va a la
	casilla, que es el único lugar donde puede leerla el dueño legítimo."""
	return _send_account_email(
		template="account_exists",
		subjects=_ACCOUNT_EXISTS_SUBJECTS,
		to_email=to_email,
		name="",
		language=language,
	)
