"""Transactional email — Resend integration.

Single canonical entry point for invitation emails. Callers must NOT use
django.core.mail.send_mail directly anymore.
"""

import logging

import resend
from django.conf import settings
from django.template.loader import render_to_string

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
