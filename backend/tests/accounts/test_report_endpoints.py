"""RF16-RF22 — reportar a una persona o a una reseña.

Guideline 1.2 no pide sólo un buzón: pide poder actuar. Por eso el reporte deja
fila con status, avisa a un humano, y guarda copia de lo denunciado.
"""

import logging
from unittest.mock import patch

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.models import Report
from accounts.services.email import EmailSendError
from tests.factories import PinFactory, RestaurantFactory, UserFactory


def _auth(user):
	client = APIClient()
	client.force_authenticate(user=user)
	return client


def _report(client, **payload):
	return client.post(reverse("report-list"), payload, format="json")


@pytest.mark.critical
@pytest.mark.django_db
@patch("accounts.services.reporting.send_report_notification_email")
def test_reporting_a_user_creates_a_pending_row(send):
	me, offender = UserFactory(), UserFactory()

	resp = _report(_auth(me), reportedUserId=offender.id, reason="harassment")

	assert resp.status_code == 201, resp.content
	report = Report.objects.get()
	assert report.reporter == me
	assert report.reported_user == offender
	assert report.pin is None
	assert report.status == Report.Status.PENDING


@pytest.mark.critical
@pytest.mark.django_db
@patch("accounts.services.reporting.send_report_notification_email")
def test_reporting_a_review_keeps_a_copy_of_what_was_reported(send):
	"""El comentario es editable: sin copia, el autor lo cambia por uno inocuo
	y el moderador revisa otra cosa."""
	me, offender = UserFactory(), UserFactory()
	pin = PinFactory(
		user=offender,
		restaurant=RestaurantFactory(),
		status="visited",
		rating=1,
		comment="texto original ofensivo",
	)

	_report(_auth(me), reportedUserId=offender.id, pinId=pin.id, reason="inappropriate")

	pin.comment = "qué lindo lugar"
	pin.save()

	report = Report.objects.get()
	assert report.reported_comment == "texto original ofensivo"
	assert report.reported_rating == 1


@pytest.mark.critical
@pytest.mark.django_db
@patch("accounts.services.reporting.send_report_notification_email")
def test_a_pin_that_does_not_belong_to_the_reported_user_is_rejected(send):
	me, offender, third = UserFactory(), UserFactory(), UserFactory()
	pin = PinFactory(
		user=third, restaurant=RestaurantFactory(), status="visited", rating=3, comment="x"
	)

	resp = _report(_auth(me), reportedUserId=offender.id, pinId=pin.id, reason="spam")

	assert resp.status_code == 400, resp.content
	assert not Report.objects.exists()


@pytest.mark.critical
@pytest.mark.django_db
@patch("accounts.services.reporting.send_report_notification_email")
def test_an_unknown_reason_is_rejected(send):
	me, offender = UserFactory(), UserFactory()

	resp = _report(_auth(me), reportedUserId=offender.id, reason="porque si")

	assert resp.status_code == 400, resp.content
	assert not Report.objects.exists()


@pytest.mark.critical
@pytest.mark.django_db
@patch("accounts.services.reporting.send_report_notification_email")
def test_reporting_notifies_a_human(send):
	me, offender = UserFactory(), UserFactory()

	_report(_auth(me), reportedUserId=offender.id, reason="harassment", detail="me insultó")

	send.assert_called_once()


@pytest.mark.critical
@pytest.mark.django_db
@patch("accounts.services.reporting.send_report_notification_email")
def test_the_report_survives_a_failed_notification(send, caplog):
	"""Perder la denuncia porque Resend está caído es peor que no avisar."""
	send.side_effect = EmailSendError("Resend caído", status_code=502)
	me, offender = UserFactory(), UserFactory()

	with caplog.at_level(logging.ERROR, logger="accounts.services.reporting"):
		resp = _report(_auth(me), reportedUserId=offender.id, reason="spam")

	assert resp.status_code == 201, resp.content
	assert Report.objects.count() == 1
	assert any(r.levelno == logging.ERROR for r in caplog.records)


@pytest.mark.critical
@pytest.mark.django_db
@patch("accounts.services.reporting.send_report_notification_email")
def test_the_reported_user_is_never_told(send):
	"""RF20: no hay endpoint que le diga a alguien que lo reportaron."""
	me, offender = UserFactory(), UserFactory()
	_report(_auth(me), reportedUserId=offender.id, reason="harassment")

	listing = _auth(offender).get(reverse("report-list"))

	assert listing.status_code in (403, 405), listing.content


@pytest.mark.critical
@pytest.mark.django_db
@patch("accounts.services.reporting.send_report_notification_email")
def test_cannot_report_yourself(send):
	me = UserFactory()

	resp = _report(_auth(me), reportedUserId=me.id, reason="spam")

	assert resp.status_code == 400, resp.content


@pytest.mark.critical
@pytest.mark.django_db
def test_reporting_requires_authentication():
	offender = UserFactory()

	resp = APIClient().post(
		reverse("report-list"), {"reportedUserId": offender.id, "reason": "spam"}, format="json"
	)

	assert resp.status_code == 401


@pytest.mark.critical
@pytest.mark.django_db
@patch("accounts.services.reporting.send_report_notification_email")
def test_account_deletion_keeps_reports_about_you_and_drops_the_ones_you_made(send):
	"""RF22: la denuncia sobre alguien sobrevive a que esa persona se borre —
	puede seguir abierta— con el usuario desvinculado. Las que emitió, no."""
	from accounts.services.account_deletion import anonymise_user

	me, offender = UserFactory(), UserFactory()
	_report(_auth(me), reportedUserId=offender.id, reason="harassment")
	_report(_auth(offender), reportedUserId=me.id, reason="spam")
	assert Report.objects.count() == 2

	anonymise_user(offender)

	assert not Report.objects.filter(reporter=offender).exists(), "las que emitió se borran"
	remaining = Report.objects.get()
	assert remaining.reporter == me
	assert remaining.reported_user is None, "queda la denuncia, sin la identidad"


@pytest.mark.critical
@pytest.mark.django_db
@patch("accounts.services.reporting.send_report_notification_email")
def test_the_report_endpoint_does_not_confirm_who_owns_a_pin(send):
	"""El campo aceptaba cualquier pin del sistema y el error distinguía entre
	"ese pin no es de esa persona" y "ese pin no existe", así que se podía
	confirmar pares (pin, dueño) de a uno. Incluye pins `to_visit` de
	desconocidos, que ningún endpoint de lectura expone."""
	me, offender, third = UserFactory(), UserFactory(), UserFactory()
	someone_elses = PinFactory(
		user=third, restaurant=RestaurantFactory(), status="visited", rating=4, comment="x"
	)

	mismatch = _report(_auth(me), reportedUserId=offender.id, pinId=someone_elses.id, reason="spam")
	nonexistent = _report(_auth(me), reportedUserId=offender.id, pinId=999999, reason="spam")

	assert mismatch.status_code == nonexistent.status_code == 400
	assert str(mismatch.json()).replace(str(someone_elses.id), "<id>") == str(
		nonexistent.json()
	).replace(
		"999999", "<id>"
	), f"distinguibles: ajeno={mismatch.json()} inexistente={nonexistent.json()}"
