"""Caracterización de GET /api/v1/feed/ — RF15 de la spec de F2.B.

Este endpoint no tenía un solo test: cero llamadas a la vista en toda la suite.
Por eso nadie notó que el `target_user` sale sin filtrar (ver el último test).
Se escriben antes de tocar el feed para el bloqueo, no después: son la red que
avisa si la migración a `visible_friend_ids` cambia lo que hoy hace.
"""

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.models import Friendship
from feed.models import Activity
from tests.factories import PinFactory, UserFactory


def _befriend(a, b):
	Friendship.objects.create(from_user=a, to_user=b, status=Friendship.Status.ACCEPTED)


def _auth(user):
	client = APIClient()
	client.force_authenticate(user=user)
	return client


def _pin_activity(user):
	"""Crea un pin y devuelve la Activity que generó el signal.

	No se crea la Activity a mano: `pins/signals.py` ya la emite al guardar el
	pin, y hacerlo a mano duplicaría filas y mediría algo que no pasa en
	producción. Lo mismo vale para las amistades, que emiten dos filas
	FRIENDSHIP (una por lado) desde `accounts/signals.py`.
	"""
	pin = PinFactory(user=user)
	return Activity.objects.get(actor=user, verb=Activity.Verb.PINNED, pin=pin)


def _actor_ids(resp):
	return {row["actor"]["id"] for row in resp.json()["results"]}


@pytest.mark.critical
@pytest.mark.django_db
def test_feed_shows_a_friends_activity():
	me, friend = UserFactory(), UserFactory()
	_befriend(me, friend)
	activity = _pin_activity(friend)

	resp = _auth(me).get(reverse("feed"))

	assert resp.status_code == 200, resp.content
	ids = [row["id"] for row in resp.json()["results"]]
	assert activity.id in ids
	# El feed son las actividades de mis amigos: el pin del amigo y la fila
	# FRIENDSHIP cuyo actor es él. La otra fila FRIENDSHIP, la que me tiene a mí
	# de actor, queda afuera por el test de abajo.
	assert _actor_ids(resp) == {friend.id}


@pytest.mark.critical
@pytest.mark.django_db
def test_feed_does_not_show_my_own_activity():
	"""`friend_ids` excluye al propio usuario a propósito. Migrar el feed a
	`visible_user_ids` —que lo incluye— cambiaría esto sin que nadie lo pida:
	es exactamente el cambio contra el que advierte visibility.py:47-52."""
	me, friend = UserFactory(), UserFactory()
	_befriend(me, friend)
	_pin_activity(me)

	resp = _auth(me).get(reverse("feed"))

	assert resp.status_code == 200, resp.content
	assert me.id not in _actor_ids(resp), "el feed no muestra la actividad propia"


@pytest.mark.critical
@pytest.mark.django_db
def test_feed_does_not_show_a_strangers_activity():
	me, stranger = UserFactory(), UserFactory()
	_pin_activity(stranger)

	resp = _auth(me).get(reverse("feed"))

	assert resp.status_code == 200, resp.content
	assert resp.json()["results"] == []


@pytest.mark.critical
@pytest.mark.django_db
def test_feed_does_not_show_a_pending_friends_activity():
	me, pending = UserFactory(), UserFactory()
	Friendship.objects.create(from_user=me, to_user=pending, status=Friendship.Status.PENDING)
	_pin_activity(pending)

	resp = _auth(me).get(reverse("feed"))

	assert resp.json()["results"] == []


@pytest.mark.critical
@pytest.mark.django_db
def test_feed_requires_authentication():
	resp = APIClient().get(reverse("feed"))

	assert resp.status_code == 401


@pytest.mark.critical
@pytest.mark.django_db
def test_feed_does_not_leak_the_email_of_a_non_friend():
	"""El feed filtra por `actor`, pero serializa `target_user` con
	UserPublicSerializer, que incluye el email.

	Cuando un amigo mío se hace amigo de un desconocido, esa actividad entra en
	mi feed —el actor es mi amigo— y me entrega el email de alguien con quien no
	tengo ninguna relación. Existe hoy, sin bloqueo de por medio.
	"""
	me, friend, stranger = UserFactory(), UserFactory(), UserFactory()
	_befriend(me, friend)
	_befriend(friend, stranger)

	resp = _auth(me).get(reverse("feed"))

	assert resp.status_code == 200, resp.content
	emails = {
		(row["targetUser"] or {}).get("email")
		for row in resp.json()["results"]
		if row.get("targetUser")
	}
	assert stranger.email not in emails, f"el feed entregó el email de un no-amigo: {emails}"
