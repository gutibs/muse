"""Tests for accounts.services.email — invitation email via Resend.

Mocks the Resend SDK at the module boundary; we don't hit the network.
"""

from unittest.mock import patch

import pytest

from accounts.services.email import EmailSendError, send_invitation_email


@pytest.mark.critical
@patch("accounts.services.email.resend.Emails.send")
def test_send_invitation_email_calls_resend_with_correct_payload(mock_send, settings):
	settings.RESEND_API_KEY = "re_test_key"
	settings.DEFAULT_FROM_EMAIL = "Muse <no-reply@lovemuse.app>"
	mock_send.return_value = {"id": "re_abc123"}

	result = send_invitation_email(
		to_email="invited@example.com",
		inviter_name="Alice",
		invitation_link="https://lovemuse.app/register",
		language="es",
	)

	assert result == {"id": "re_abc123"}
	mock_send.assert_called_once()
	payload = mock_send.call_args[0][0]
	assert payload["to"] == ["invited@example.com"]
	assert payload["from"] == "Muse <no-reply@lovemuse.app>"
	assert "Alice" in payload["subject"]
	assert "Muse" in payload["subject"]
	# Both HTML and plain-text variants must be rendered
	assert "Alice" in payload["html"]
	assert "Alice" in payload["text"]
	assert "https://lovemuse.app/register" in payload["html"]
	assert "https://lovemuse.app/register" in payload["text"]


@pytest.mark.critical
@patch("accounts.services.email.resend.Emails.send")
def test_send_invitation_email_raises_502_when_resend_fails(mock_send, settings):
	settings.RESEND_API_KEY = "re_test_key"
	mock_send.side_effect = RuntimeError("Resend API unreachable")

	with pytest.raises(EmailSendError) as exc_info:
		send_invitation_email(
			to_email="invited@example.com",
			inviter_name="Alice",
			invitation_link="https://lovemuse.app/register",
		)

	assert exc_info.value.status_code == 502
	assert "Resend API unreachable" in exc_info.value.message


@pytest.mark.critical
def test_send_invitation_email_raises_503_when_api_key_missing(settings):
	settings.RESEND_API_KEY = ""

	with pytest.raises(EmailSendError) as exc_info:
		send_invitation_email(
			to_email="invited@example.com",
			inviter_name="Alice",
			invitation_link="https://lovemuse.app/register",
		)

	assert exc_info.value.status_code == 503
	assert "RESEND_API_KEY" in exc_info.value.message


@patch("accounts.services.email.resend.Emails.send")
def test_send_invitation_email_falls_back_to_english_for_unknown_language(mock_send, settings):
	settings.RESEND_API_KEY = "re_test_key"
	settings.DEFAULT_FROM_EMAIL = "Muse <no-reply@lovemuse.app>"
	mock_send.return_value = {"id": "re_abc123"}

	send_invitation_email(
		to_email="invited@example.com",
		inviter_name="Alice",
		invitation_link="https://lovemuse.app/register",
		language="fr",  # not in SUPPORTED_LANGUAGES
	)

	payload = mock_send.call_args[0][0]
	# English subject template: "{inviter_name} invited you to Muse"
	assert "invited you to Muse" in payload["subject"]
