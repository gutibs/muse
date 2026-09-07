"""El resumen diario no puede contar lo que el destinatario no puede ver.

Es el mismo oráculo que F2.A cerró, entrando por otra puerta: si el resumen
dice "tu amigo guardó un lugar" sobre un pin privado, lo delata igual que
mostrarlo en pantalla. Por eso el resumen se arma en el momento de mandarlo y
no antes — un pin que cambió de nivel desde que ocurrió la actividad tiene que
quedar afuera.
"""

import zoneinfo
from datetime import timedelta
from unittest.mock import patch

import pytest
from django.utils import timezone

from accounts.models import Block, Friendship
from feed.models import Activity
from notifications.models import DigestLog
from notifications.services import digest
from pins.models import Pin, Visibility
from tests.factories.friendships import FriendshipFactory
from tests.factories.pins import PinFactory
from tests.factories.users import UserFactory


def _friends(a, b):
	FriendshipFactory(from_user=a, to_user=b, status=Friendship.Status.ACCEPTED)


def _pin_with_activity(owner, *, visibility=Visibility.PUBLIC):
	pin = PinFactory(user=owner, status=Pin.Status.VISITED, rating=5, visibility=visibility)
	# El signal de pins ya crea la Activity; la buscamos en vez de duplicarla.
	return pin, Activity.objects.filter(pin=pin).first()


@pytest.mark.critical
@pytest.mark.django_db
def test_un_pin_privado_no_entra_en_el_resumen():
	me, friend = UserFactory(), UserFactory()
	_friends(me, friend)
	_pin_with_activity(friend, visibility=Visibility.PRIVATE)

	assert digest.collect(me) == []


@pytest.mark.critical
@pytest.mark.django_db
def test_un_pin_que_pasa_a_privado_despues_tampoco_entra():
	"""El caso que obliga a armar el resumen al mandarlo y no antes."""
	me, friend = UserFactory(), UserFactory()
	_friends(me, friend)
	pin, _ = _pin_with_activity(friend, visibility=Visibility.PUBLIC)

	# Estaba visible cuando ocurrió.
	assert len(digest.collect(me)) == 1

	pin.visibility = Visibility.PRIVATE
	pin.save()

	# Y deja de estarlo antes de la hora del resumen.
	assert digest.collect(me) == []


@pytest.mark.critical
@pytest.mark.django_db
def test_un_bloqueo_saca_al_bloqueado_del_resumen():
	me, other = UserFactory(), UserFactory()
	_friends(me, other)
	_pin_with_activity(other, visibility=Visibility.PUBLIC)
	assert len(digest.collect(me)) == 1

	Block.objects.create(blocker=me, blocked=other)
	assert digest.collect(me) == []


@pytest.mark.django_db
def test_las_ediciones_no_cuentan():
	"""Corregir una reseña tres veces no le llega a nadie."""
	me, friend = UserFactory(), UserFactory()
	_friends(me, friend)
	pin, _ = _pin_with_activity(friend, visibility=Visibility.PUBLIC)

	for comentario in ("uno", "dos", "tres"):
		pin.comment = comentario
		pin.save()

	assert Activity.objects.filter(pin=pin, verb=Activity.Verb.UPDATED).count() == 3
	# El resumen sigue contando una sola cosa: que lo guardó.
	assert len(digest.collect(me)) == 1


@pytest.mark.django_db
def test_lo_viejo_queda_fuera_de_la_ventana():
	me, friend = UserFactory(), UserFactory()
	_friends(me, friend)
	_, activity = _pin_with_activity(friend)
	Activity.objects.filter(pk=activity.pk).update(
		created_at=timezone.now() - timedelta(hours=digest.WINDOW_HOURS + 1)
	)

	assert digest.collect(me) == []


@pytest.mark.django_db
def test_no_se_manda_resumen_vacio():
	"""Una notificación que dice 'no pasó nada' es la forma de que la apaguen."""
	me, friend = UserFactory(), UserFactory()
	_friends(me, friend)

	with patch("notifications.services.digest.push_to_user") as push:
		assert digest.send_for(me) is False
	push.assert_not_called()
	assert DigestLog.objects.count() == 0


@pytest.mark.django_db
def test_no_se_manda_dos_veces_el_mismo_dia():
	me, friend = UserFactory(), UserFactory()
	_friends(me, friend)
	_pin_with_activity(friend)

	with patch("notifications.services.digest.push_to_user") as push:
		assert digest.send_for(me) is True
		assert digest.send_for(me) is False

	assert push.call_count == 1
	assert DigestLog.objects.filter(user=me).count() == 1


@pytest.mark.django_db
def test_respeta_la_preferencia_apagada():
	me, friend = UserFactory(), UserFactory()
	_friends(me, friend)
	_pin_with_activity(friend)
	me.profile.notify_daily_digest = False
	me.profile.save()

	with patch("notifications.services.digest.push_to_user") as push:
		assert digest.send_for(me) is False
	push.assert_not_called()


@pytest.mark.django_db
def test_la_hora_es_la_local_de_cada_persona():
	"""Con el servidor en Buenos Aires y usuarios en Hong Kong, once horas."""
	hk = UserFactory()
	hk.profile.timezone = "Asia/Hong_Kong"
	hk.profile.digest_hour = 19
	hk.profile.save()

	# 19:00 en Hong Kong es 11:00 UTC.
	once_utc = timezone.now().replace(hour=11, minute=0, tzinfo=zoneinfo.ZoneInfo("UTC"))
	assert digest.is_due(hk.profile, now=once_utc) is True

	# Y a las 19:00 del servidor (22:00 UTC) todavía no le toca.
	veintidos_utc = once_utc.replace(hour=22)
	assert digest.is_due(hk.profile, now=veintidos_utc) is False


@pytest.mark.django_db
def test_una_timezone_invalida_no_deja_a_nadie_sin_resumen():
	user = UserFactory()
	user.profile.timezone = "No/Existe"
	user.profile.digest_hour = 12
	user.profile.save()

	mediodia_utc = timezone.now().replace(hour=12, minute=0, tzinfo=zoneinfo.ZoneInfo("UTC"))
	assert digest.is_due(user.profile, now=mediodia_utc) is True
