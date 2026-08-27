"""RF19 — la cola de moderación.

Guideline 1.2 no pide sólo recibir denuncias: pide poder actuar. Sin un lugar
donde verlas y marcarlas resueltas, el endpoint de reportes es un buzón sin
proceso. El admin de Django es ese lugar; no hay pantalla propia y no hace
falta.
"""

import pytest
from django.contrib.admin.sites import site
from django.urls import reverse

from accounts.models import Report
from tests.factories import UserFactory


@pytest.mark.critical
@pytest.mark.django_db
def test_reports_are_registered_in_the_admin():
	assert Report in site._registry, "sin esto no hay dónde resolver una denuncia"


@pytest.mark.critical
@pytest.mark.django_db
def test_the_queue_can_be_filtered_by_status_and_reason():
	model_admin = site._registry[Report]

	assert "status" in model_admin.list_filter
	assert "reason" in model_admin.list_filter


@pytest.mark.critical
@pytest.mark.django_db
def test_resolving_a_report_stamps_when():
	"""La constancia de que se actuó, que es lo que la guideline mira."""
	reporter, offender = UserFactory(), UserFactory()
	report = Report.objects.create(
		reporter=reporter, reported_user=offender, reason=Report.Reason.SPAM
	)
	assert report.resolved_at is None

	report.status = Report.Status.ACTIONED
	report.save()

	report.refresh_from_db()
	assert report.resolved_at is not None, "resolver tiene que dejar fecha"


@pytest.mark.critical
@pytest.mark.django_db
def test_a_report_left_pending_has_no_resolution_date():
	reporter, offender = UserFactory(), UserFactory()
	report = Report.objects.create(
		reporter=reporter, reported_user=offender, reason=Report.Reason.SPAM
	)

	report.detail = "algo más"
	report.save()

	report.refresh_from_db()
	assert report.resolved_at is None


@pytest.mark.critical
@pytest.mark.django_db
def test_pending_reports_come_first_in_the_queue():
	reporter, a, b = UserFactory(), UserFactory(), UserFactory()
	done = Report.objects.create(
		reporter=reporter,
		reported_user=a,
		reason=Report.Reason.SPAM,
		status=Report.Status.DISMISSED,
	)
	pending = Report.objects.create(reporter=reporter, reported_user=b, reason=Report.Reason.SPAM)

	assert list(Report.objects.all()) == [pending, done]


@pytest.mark.critical
@pytest.mark.django_db
def test_the_admin_can_see_the_reported_content_snapshot():
	model_admin = site._registry[Report]
	fields = set(model_admin.readonly_fields) | set(model_admin.list_display)

	assert "reported_comment" in fields, "el moderador tiene que ver qué se denunció"


@pytest.mark.critical
@pytest.mark.django_db
def test_the_reports_admin_url_exists():
	assert reverse("admin:accounts_report_changelist")
