"""El email del código de recuperación, contra el boundary de Resend.

Mismo patrón que test_invitation_email.py: se mockea el SDK, no el service.
"""

from unittest.mock import patch

import pytest

from accounts.services.email import EmailSendError, send_password_reset_email


@pytest.mark.critical
@patch("accounts.services.email.resend.Emails.send")
def test_password_reset_email_carries_the_code_in_both_bodies(mock_send, settings):
	settings.RESEND_API_KEY = "re_test_key"
	settings.DEFAULT_FROM_EMAIL = "Muse <no-reply@lovemuse.app>"
	mock_send.return_value = {"id": "re_abc123"}

	result = send_password_reset_email(to_email="forgot@example.com", code="123456", language="es")

	assert result == {"id": "re_abc123"}
	payload = mock_send.call_args[0][0]
	assert payload["to"] == ["forgot@example.com"]
	assert payload["from"] == "Muse <no-reply@lovemuse.app>"
	assert "123456" in payload["html"]
	assert "123456" in payload["text"]
	# El código no viaja en el asunto: los asuntos quedan en previews de
	# notificación y en logs de terceros.
	assert "123456" not in payload["subject"]


@pytest.mark.critical
@patch("accounts.services.email.resend.Emails.send")
def test_password_reset_email_raises_502_when_resend_fails(mock_send, settings):
	settings.RESEND_API_KEY = "re_test_key"
	mock_send.side_effect = RuntimeError("Resend API unreachable")

	with pytest.raises(EmailSendError) as exc_info:
		send_password_reset_email(to_email="forgot@example.com", code="123456")

	assert exc_info.value.status_code == 502


@pytest.mark.critical
@patch("accounts.services.email.resend.Emails.send")
def test_password_reset_email_renders_each_supported_language(mock_send, settings):
	"""RF15: es, en, it — y un idioma desconocido cae al default sin romper."""
	settings.RESEND_API_KEY = "re_test_key"
	mock_send.return_value = {"id": "re_abc123"}

	subjects = {}
	for lang in ("es", "en", "it", "fr"):
		send_password_reset_email(to_email="forgot@example.com", code="123456", language=lang)
		subjects[lang] = mock_send.call_args[0][0]["subject"]

	assert len({subjects["es"], subjects["en"], subjects["it"]}) == 3
	assert subjects["fr"] == subjects["en"]
