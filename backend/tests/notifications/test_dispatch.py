"""La cola de notificaciones inmediatas.

Cubre los tres agujeros que encontró la revisión adversarial de la spec: jobs
tomados por un proceso que murió, reenvío tras restaurar un backup, y entrega
de cosas viejas cuando el despachador estuvo caído.
"""

from datetime import timedelta
from unittest.mock import patch

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import Friendship
from notifications.models import DeviceToken, NotificationJob
from notifications.services import dispatch
from notifications.services.fcm import FCMError
from tests.factories.friendships import FriendshipFactory
from tests.factories.users import UserFactory

PASSWORD = "test-pass-123"


def _auth(user):
	tokens = (
		APIClient()
		.post(
			reverse("token_obtain"),
			{"username": user.username, "password": PASSWORD},
			format="json",
		)
		.json()
	)
	return APIClient(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")


def _job(recipient, actor=None, **kwargs):
	defaults = {
		"kind": NotificationJob.Kind.FRIENDSHIP_REQUEST,
		"idempotency_key": f"test:{timezone.now().timestamp()}:{recipient.pk}",
	}
	defaults.update(kwargs)
	return NotificationJob.objects.create(recipient=recipient, actor=actor, **defaults)


# --- Encolado desde los signals -------------------------------------------
#
# Todos usan `django_capture_on_commit_callbacks`: los signals encolan con
# `transaction.on_commit`, y en un test envuelto en transacción ese callback no
# corre nunca. Sin el fixture, los tests que esperan CERO jobs pasan por la
# razón equivocada — no porque la preferencia frene el encolado, sino porque
# nada se ejecutó.


@pytest.mark.django_db
def test_una_solicitud_de_amistad_encola_para_el_destinatario(django_capture_on_commit_callbacks):
	sender, receiver = UserFactory(), UserFactory()
	with django_capture_on_commit_callbacks(execute=True):
		FriendshipFactory(from_user=sender, to_user=receiver, status=Friendship.Status.PENDING)

	job = NotificationJob.objects.get()
	assert job.recipient == receiver
	assert job.kind == NotificationJob.Kind.FRIENDSHIP_REQUEST


@pytest.mark.django_db
def test_aceptar_le_avisa_a_quien_la_mando(django_capture_on_commit_callbacks):
	sender, receiver = UserFactory(), UserFactory()
	with django_capture_on_commit_callbacks(execute=True):
		friendship = FriendshipFactory(
			from_user=sender, to_user=receiver, status=Friendship.Status.PENDING
		)
	NotificationJob.objects.all().delete()

	with django_capture_on_commit_callbacks(execute=True):
		friendship.status = Friendship.Status.ACCEPTED
		friendship.save()

	job = NotificationJob.objects.get()
	assert job.recipient == sender, "le avisa a quien pidió, no a quien aceptó"
	assert job.kind == NotificationJob.Kind.FRIENDSHIP_ACCEPTED


@pytest.mark.django_db
def test_no_encola_si_la_preferencia_esta_apagada(django_capture_on_commit_callbacks):
	sender, receiver = UserFactory(), UserFactory()
	receiver.profile.notify_friend_request = False
	receiver.profile.save()

	with django_capture_on_commit_callbacks(execute=True):
		FriendshipFactory(from_user=sender, to_user=receiver, status=Friendship.Status.PENDING)
	assert NotificationJob.objects.count() == 0


@pytest.mark.django_db
def test_apagar_una_preferencia_no_apaga_las_otras(django_capture_on_commit_callbacks):
	sender, receiver = UserFactory(), UserFactory()
	receiver.profile.notify_daily_digest = False
	receiver.profile.save()

	with django_capture_on_commit_callbacks(execute=True):
		FriendshipFactory(from_user=sender, to_user=receiver, status=Friendship.Status.PENDING)
	assert NotificationJob.objects.count() == 1


@pytest.mark.django_db
def test_el_encolado_no_llama_a_fcm(django_capture_on_commit_callbacks):
	"""Ningún envío ocurre dentro del request. Es el punto de tener cola."""
	sender, receiver = UserFactory(), UserFactory()
	with patch("notifications.services.fcm.send") as send:
		with django_capture_on_commit_callbacks(execute=True):
			FriendshipFactory(from_user=sender, to_user=receiver, status=Friendship.Status.PENDING)
	send.assert_not_called()
	assert NotificationJob.objects.count() == 1, "encoló, pero sin mandar nada"


# --- Idempotencia ----------------------------------------------------------


@pytest.mark.django_db
def test_el_mismo_evento_no_se_encola_dos_veces():
	"""Restaurar un backup no puede volver a mandar lo ya entregado."""
	receiver, actor = UserFactory(), UserFactory()
	key = "friendship:42:request"

	primero = dispatch.notify(
		recipient=receiver,
		actor=actor,
		kind=NotificationJob.Kind.FRIENDSHIP_REQUEST,
		idempotency_key=key,
	)
	segundo = dispatch.notify(
		recipient=receiver,
		actor=actor,
		kind=NotificationJob.Kind.FRIENDSHIP_REQUEST,
		idempotency_key=key,
	)

	assert primero is not None
	assert segundo is None
	assert NotificationJob.objects.count() == 1


@pytest.mark.django_db
def test_nadie_se_notifica_a_si_mismo():
	user = UserFactory()
	assert (
		dispatch.notify(
			recipient=user,
			actor=user,
			kind=NotificationJob.Kind.FRIENDSHIP_REQUEST,
			idempotency_key="self:1",
		)
		is None
	)


# --- El despachador --------------------------------------------------------


@pytest.mark.django_db
def test_un_job_pendiente_se_manda_y_queda_sent():
	receiver = UserFactory()
	DeviceToken.objects.create(user=receiver, token="tok-1")
	_job(receiver, UserFactory())

	with patch("notifications.services.fcm.send") as send:
		stats = dispatch.run_pending()

	assert send.call_count == 1
	assert stats["sent"] == 1
	assert NotificationJob.objects.get().state == NotificationJob.State.SENT


@pytest.mark.critical
@pytest.mark.django_db
def test_un_job_tomado_por_un_proceso_muerto_vuelve_a_la_cola():
	"""El deploy hace `down` + `up` en cada push: pasa todas las semanas."""
	receiver = UserFactory()
	DeviceToken.objects.create(user=receiver, token="tok-1")
	job = _job(receiver, UserFactory())
	NotificationJob.objects.filter(pk=job.pk).update(
		state=NotificationJob.State.PROCESSING,
		locked_at=timezone.now() - timedelta(minutes=NotificationJob.LOCK_TIMEOUT_MINUTES + 1),
	)

	with patch("notifications.services.fcm.send"):
		stats = dispatch.run_pending()

	assert stats["released"] == 1
	assert stats["sent"] == 1
	assert NotificationJob.objects.get().state == NotificationJob.State.SENT


@pytest.mark.django_db
def test_un_job_recien_tomado_no_se_le_roba_a_nadie():
	receiver = UserFactory()
	job = _job(receiver, UserFactory())
	NotificationJob.objects.filter(pk=job.pk).update(
		state=NotificationJob.State.PROCESSING, locked_at=timezone.now()
	)

	with patch("notifications.services.fcm.send") as send:
		stats = dispatch.run_pending()

	assert stats["released"] == 0
	send.assert_not_called()


@pytest.mark.django_db
def test_lo_viejo_se_descarta_en_vez_de_entregarse():
	"""Si el despachador estuvo caído, nadie quiere lo de ayer ahora."""
	receiver = UserFactory()
	DeviceToken.objects.create(user=receiver, token="tok-1")
	job = _job(receiver, UserFactory())
	NotificationJob.objects.filter(pk=job.pk).update(
		created_at=timezone.now() - timedelta(hours=NotificationJob.STALE_HOURS + 1)
	)

	with patch("notifications.services.fcm.send") as send:
		stats = dispatch.run_pending()

	send.assert_not_called()
	assert stats["discarded"] == 1
	assert NotificationJob.objects.get().state == NotificationJob.State.DISCARDED


@pytest.mark.django_db
def test_un_fallo_se_reintenta_y_despues_queda_failed():
	receiver = UserFactory()
	DeviceToken.objects.create(user=receiver, token="tok-1")
	_job(receiver, UserFactory())

	with patch("notifications.services.fcm.send", side_effect=FCMError("503")):
		for _ in range(NotificationJob.MAX_ATTEMPTS):
			dispatch.run_pending()

	job = NotificationJob.objects.get()
	assert job.attempts == NotificationJob.MAX_ATTEMPTS
	assert job.state == NotificationJob.State.FAILED
	assert "503" in job.last_error


@pytest.mark.django_db
def test_un_token_muerto_se_borra_y_el_resto_se_entrega():
	receiver = UserFactory()
	DeviceToken.objects.create(user=receiver, token="muerto")
	DeviceToken.objects.create(user=receiver, token="vivo")
	_job(receiver, UserFactory())

	def responder(token, **kwargs):
		if token == "muerto":
			raise FCMError("UNREGISTERED", dead_token=True)

	with patch("notifications.services.fcm.send", side_effect=responder):
		stats = dispatch.run_pending()

	assert stats["sent"] == 1
	assert DeviceToken.objects.filter(user=receiver).count() == 1
	assert DeviceToken.objects.get().token == "vivo"


@pytest.mark.django_db
def test_la_preferencia_se_revalida_al_despachar():
	receiver = UserFactory()
	DeviceToken.objects.create(user=receiver, token="tok-1")
	_job(receiver, UserFactory())

	receiver.profile.notify_friend_request = False
	receiver.profile.save()

	with patch("notifications.services.fcm.send") as send:
		stats = dispatch.run_pending()

	send.assert_not_called()
	assert stats["discarded"] == 1


# --- Registro de dispositivos ---------------------------------------------


@pytest.mark.django_db
def test_registrar_el_mismo_token_dos_veces_deja_una_fila():
	user = UserFactory()
	client = _auth(user)
	url = reverse("notification-devices")

	assert client.post(url, {"token": "abc"}, format="json").status_code == 200
	assert client.post(url, {"token": "abc"}, format="json").status_code == 200
	assert DeviceToken.objects.filter(user=user).count() == 1


@pytest.mark.django_db
def test_un_token_de_otra_cuenta_cambia_de_dueño():
	"""Dos cuentas en el mismo teléfono: la primera deja de recibir."""
	a, b = UserFactory(), UserFactory()
	DeviceToken.objects.create(user=a, token="mismo-telefono")

	_auth(b).post(reverse("notification-devices"), {"token": "mismo-telefono"}, format="json")

	assert DeviceToken.objects.count() == 1
	assert DeviceToken.objects.get().user == b


@pytest.mark.django_db
def test_se_conservan_como_maximo_cinco_dispositivos():
	user = UserFactory()
	client = _auth(user)
	url = reverse("notification-devices")

	for i in range(DeviceToken.MAX_PER_USER + 2):
		client.post(url, {"token": f"tok-{i}"}, format="json")

	assert DeviceToken.objects.filter(user=user).count() == DeviceToken.MAX_PER_USER
	assert not DeviceToken.objects.filter(token="tok-0").exists()


@pytest.mark.django_db
def test_el_logout_baja_el_token():
	user = UserFactory()
	client = _auth(user)
	url = reverse("notification-devices")
	client.post(url, {"token": "abc"}, format="json")

	assert client.delete(url, {"token": "abc"}, format="json").status_code == 204
	assert DeviceToken.objects.count() == 0


@pytest.mark.django_db
def test_registrar_un_dispositivo_exige_sesion():
	assert APIClient().post(
		reverse("notification-devices"), {"token": "abc"}, format="json"
	).status_code in (401, 403)


# --- Idioma ----------------------------------------------------------------


@pytest.mark.django_db
@pytest.mark.parametrize(
	("language", "esperado"),
	[
		("en", "New friend request"),
		("es", "Nueva solicitud de amistad"),
		("it", "Nuova richiesta di amicizia"),
	],
)
def test_el_texto_sale_en_el_idioma_del_destinatario(language, esperado):
	"""El idioma sale del perfil, no de un header.

	El push lo inicia el servidor: cuando hay que avisarle algo a alguien, esa
	persona no está haciendo ninguna llamada de la que leer `Accept-Language`.
	"""
	receiver, actor = UserFactory(), UserFactory()
	receiver.profile.language = language
	receiver.profile.save()
	actor.profile.display_name = "Jess"
	actor.profile.save()

	job = _job(receiver, actor, context={"actor_name": "Jess"})
	title, body = dispatch.render(job)

	assert title == esperado
	assert "Jess" in body


@pytest.mark.django_db
def test_los_nombres_largos_se_truncan():
	"""En el catálogo real hay nombres de 60+ caracteres."""
	largo = "The Peppertree Restaurant - La Veranda Resort Phu Quoc MGallery y más"
	assert len(dispatch.truncate(largo, dispatch.TITLE_MAX)) <= dispatch.TITLE_MAX
	assert dispatch.truncate(largo, dispatch.TITLE_MAX).endswith("…")
	# Lo que entra no se toca.
	assert dispatch.truncate("corto", dispatch.TITLE_MAX) == "corto"
