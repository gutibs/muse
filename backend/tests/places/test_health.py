"""El chequeo de salud de Google Places y el aviso por mail.

Existe por el corte del 2026-09-08: la cuenta de billing de GCP quedó cerrada,
Places devolvió PERMISSION_DENIED por tiempo indeterminado y el corte se
descubrió de casualidad, corriendo la suite antes de un merge.

Lo que estos tests fijan no es "el chequeo anda", es el ruido: un mail por
transición y no uno por corrida, ningún mail por un timeout suelto, y un aviso
que no se pierde si Resend falla justo cuando hay que mandarlo.
"""

from datetime import timedelta
from unittest.mock import patch

import pytest
from django.core.management import call_command
from django.utils import timezone

from places.models import IntegrationHealth
from places.services import health
from places.services.google_places import GooglePlacesError


def _caido(detail="HTTP 403: PERMISSION_DENIED — billing account closed"):
	return GooglePlacesError("Places API error.", detail=detail)


# --- La sonda -------------------------------------------------------------


@patch("places.services.google_places.autocomplete")
def test_google_respondiendo_es_salud(mock_autocomplete):
	mock_autocomplete.return_value = [{"placeId": "abc"}]

	result = health.probe_places()

	assert result.healthy
	# Una sola llamada: el reintento cuesta cuota y sólo se paga si hizo falta.
	assert mock_autocomplete.call_count == 1


@patch("places.services.google_places.autocomplete")
def test_cero_resultados_sigue_siendo_salud(mock_autocomplete):
	"""Un 200 vacío habla de los datos de Google, no de si nos atiende."""
	mock_autocomplete.return_value = []

	assert health.probe_places().healthy


@patch("places.services.google_places.autocomplete")
def test_un_fallo_aislado_no_es_un_corte(mock_autocomplete):
	"""El reintento existe para no mandar mails de cortes que no pasaron."""
	mock_autocomplete.side_effect = [_caido("timeout"), [{"placeId": "abc"}]]

	result = health.probe_places(pause=0)

	assert result.healthy
	assert mock_autocomplete.call_count == 2


@patch("places.services.google_places.autocomplete")
def test_dos_fallos_seguidos_son_un_corte(mock_autocomplete):
	mock_autocomplete.side_effect = _caido()

	result = health.probe_places(pause=0)

	assert not result.healthy
	# El motivo real de Google, no un "falló" genérico: es lo que hace que el
	# mail sirva para diagnosticar sin entrar al server.
	assert "PERMISSION_DENIED" in result.error


@patch("places.services.google_places.autocomplete")
def test_sin_key_configurada_cuenta_como_corte(mock_autocomplete):
	mock_autocomplete.side_effect = GooglePlacesError(
		"Google Places API is not configured.", status_code=503
	)

	result = health.probe_places(pause=0)

	assert not result.healthy
	assert "not configured" in result.error


# --- El estado entre corridas ---------------------------------------------


@pytest.mark.django_db
def test_la_primera_corrida_sana_no_avisa():
	outcome = health.update_state(health.GOOGLE_PLACES, health.CheckResult(healthy=True))

	assert not outcome.should_alert
	fila = IntegrationHealth.objects.get(service=health.GOOGLE_PLACES)
	assert fila.is_healthy
	assert fila.alerted


@pytest.mark.django_db
def test_la_primera_corrida_rota_avisa():
	outcome = health.update_state(
		health.GOOGLE_PLACES, health.CheckResult(healthy=False, error="HTTP 403")
	)

	assert outcome.should_alert
	assert not outcome.recovered
	assert not IntegrationHealth.objects.get(service=health.GOOGLE_PLACES).alerted


@pytest.mark.django_db
def test_de_sano_a_caido_avisa_y_guarda_el_motivo():
	health.update_state(health.GOOGLE_PLACES, health.CheckResult(healthy=True))

	outcome = health.update_state(
		health.GOOGLE_PLACES, health.CheckResult(healthy=False, error="HTTP 403: denied")
	)

	assert outcome.should_alert
	fila = IntegrationHealth.objects.get(service=health.GOOGLE_PLACES)
	assert not fila.is_healthy
	assert fila.last_error == "HTTP 403: denied"


@pytest.mark.django_db
def test_caido_y_ya_avisado_no_vuelve_a_avisar():
	"""Tres días de corte son 2 mails, no 12."""
	health.update_state(health.GOOGLE_PLACES, health.CheckResult(healthy=True))
	primera = health.update_state(
		health.GOOGLE_PLACES, health.CheckResult(healthy=False, error="HTTP 403")
	)
	health.mark_alerted(primera.state)

	segunda = health.update_state(
		health.GOOGLE_PLACES, health.CheckResult(healthy=False, error="HTTP 403")
	)

	assert not segunda.should_alert


@pytest.mark.django_db
def test_la_recuperacion_avisa_con_cuanto_duro():
	caida = health.update_state(
		health.GOOGLE_PLACES, health.CheckResult(healthy=False, error="HTTP 403")
	)
	health.mark_alerted(caida.state)
	IntegrationHealth.objects.filter(service=health.GOOGLE_PLACES).update(
		changed_at=timezone.now() - timedelta(hours=8)
	)

	outcome = health.update_state(health.GOOGLE_PLACES, health.CheckResult(healthy=True))

	assert outcome.should_alert
	assert outcome.recovered
	assert timedelta(hours=7, minutes=55) < outcome.downtime < timedelta(hours=8, minutes=5)


@pytest.mark.django_db
def test_un_chequeo_sin_novedad_no_mueve_la_fecha_del_cambio():
	"""`changed_at` es cuándo cambió, no cuándo se miró: la duración depende de eso."""
	health.update_state(health.GOOGLE_PLACES, health.CheckResult(healthy=True))
	antes = IntegrationHealth.objects.get(service=health.GOOGLE_PLACES)

	health.update_state(health.GOOGLE_PLACES, health.CheckResult(healthy=True))
	despues = IntegrationHealth.objects.get(service=health.GOOGLE_PLACES)

	assert despues.changed_at == antes.changed_at
	assert despues.checked_at > antes.checked_at


# --- El comando, de punta a punta -----------------------------------------


@pytest.mark.django_db
@patch("accounts.services.email.resend.Emails.send")
@patch("places.services.google_places.autocomplete")
def test_el_comando_manda_el_mail_con_lo_que_dijo_google(mock_autocomplete, mock_send, settings):
	settings.RESEND_API_KEY = "re_test_key"
	settings.MODERATION_EMAIL = "ops@lovemuse.app"
	mock_autocomplete.side_effect = _caido()
	mock_send.return_value = {"id": "re_abc"}

	call_command("check_integrations", "--no-retry")

	payload = mock_send.call_args[0][0]
	assert payload["to"] == ["ops@lovemuse.app"]
	assert "DOWN" in payload["subject"]
	assert "PERMISSION_DENIED" in payload["text"]
	assert IntegrationHealth.objects.get(service=health.GOOGLE_PLACES).alerted


@pytest.mark.django_db
@patch("accounts.services.email.resend.Emails.send")
@patch("places.services.google_places.autocomplete")
def test_el_comando_no_manda_nada_cuando_todo_anda(mock_autocomplete, mock_send, settings):
	settings.RESEND_API_KEY = "re_test_key"
	mock_autocomplete.return_value = [{"placeId": "abc"}]

	call_command("check_integrations", "--no-retry")

	mock_send.assert_not_called()


@pytest.mark.django_db
@patch("accounts.services.email.resend.Emails.send")
@patch("places.services.google_places.autocomplete")
def test_si_el_mail_falla_el_aviso_queda_pendiente(mock_autocomplete, mock_send, settings):
	"""El caso que justifica que `alerted` sea un campo aparte de `is_healthy`.

	Con un solo campo, el cambio de estado ya estaría consumido y este corte no
	se avisaría nunca.
	"""
	settings.RESEND_API_KEY = "re_test_key"
	mock_autocomplete.side_effect = _caido()
	mock_send.side_effect = RuntimeError("Resend unreachable")

	call_command("check_integrations", "--no-retry")

	assert not IntegrationHealth.objects.get(service=health.GOOGLE_PLACES).alerted

	# La corrida siguiente reintenta el aviso en vez de tragárselo.
	mock_send.side_effect = None
	mock_send.return_value = {"id": "re_abc"}
	call_command("check_integrations", "--no-retry")

	mock_send.assert_called()
	assert IntegrationHealth.objects.get(service=health.GOOGLE_PLACES).alerted


@patch("places.services.google_places.autocomplete")
def test_una_excepcion_inesperada_tambien_es_un_corte(mock_autocomplete):
	"""Un monitor que se cae con lo que no esperaba deja de ser un monitor.

	Si la excepción sube, `update_state` no corre y no queda registro de nada:
	el corte pasa tan desapercibido como antes de que esto existiera.
	"""
	mock_autocomplete.side_effect = AttributeError("'str' object has no attribute 'get'")

	result = health.probe_places(pause=0)

	assert not result.healthy
	assert "AttributeError" in result.error


@pytest.mark.django_db
def test_el_aviso_de_recuperacion_reintentado_no_pierde_la_duracion():
	"""El caso que se destapa cuando Resend falla justo en la recuperación.

	La duración se calcula al detectar la recuperación, pero el mail puede salir
	seis horas después. Para entonces `changed_at` ya es el momento de la
	recuperación: sin persistirla, el aviso sale diciendo "Downtime: unknown",
	que es el único dato que ese mail lleva.
	"""
	caida = health.update_state(
		health.GOOGLE_PLACES, health.CheckResult(healthy=False, error="403")
	)
	health.mark_alerted(caida.state)
	IntegrationHealth.objects.filter(service=health.GOOGLE_PLACES).update(
		changed_at=timezone.now() - timedelta(hours=5)
	)

	primero = health.update_state(health.GOOGLE_PLACES, health.CheckResult(healthy=True))
	assert primero.downtime is not None
	# El mail falla, así que nadie llama a mark_alerted y el aviso queda pendiente.

	reintento = health.update_state(health.GOOGLE_PLACES, health.CheckResult(healthy=True))

	assert reintento.should_alert
	assert reintento.downtime == primero.downtime
