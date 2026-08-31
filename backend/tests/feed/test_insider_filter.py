"""F1.7 — `GET /feed/?insider=true`: sólo lo que publican los verificados.

El feed no leía ningún query param: `get_queryset` aplicaba visibilidad y
nada más. Este es el primer filtro que entra, así que también fija la forma —
el mismo booleano de texto que ya usan los pins (`favourite`), y no un
segundo dialecto al lado del primero.
"""

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.models import Friendship
from tests.factories import PinFactory, UserFactory


def _befriend(a, b):
	Friendship.objects.create(from_user=a, to_user=b, status=Friendship.Status.ACCEPTED)


def _auth(user):
	client = APIClient()
	client.force_authenticate(user=user)
	return client


def _insider(username="insider"):
	user = UserFactory(username=username)
	user.profile.is_verified_insider = True
	user.profile.save()
	return user


def _actors(resp):
	return {row["actor"]["id"] for row in resp.json()["results"]}


@pytest.mark.django_db
def test_the_filter_keeps_only_activity_from_insiders():
	me = UserFactory(username="me")
	insider = _insider()
	anyone = UserFactory(username="anyone")
	_befriend(me, insider)
	_befriend(me, anyone)
	PinFactory(user=insider)
	PinFactory(user=anyone)

	resp = _auth(me).get(reverse("feed"), {"insider": "true"})

	assert _actors(resp) == {insider.id}


@pytest.mark.django_db
def test_without_the_filter_the_feed_is_unchanged():
	me = UserFactory(username="me")
	insider = _insider()
	anyone = UserFactory(username="anyone")
	_befriend(me, insider)
	_befriend(me, anyone)
	PinFactory(user=insider)
	PinFactory(user=anyone)

	resp = _auth(me).get(reverse("feed"))

	assert _actors(resp) == {insider.id, anyone.id}


@pytest.mark.critical
@pytest.mark.django_db
def test_the_filter_does_not_widen_who_you_can_see():
	"""Filtrar no es una puerta: un Insider que no es tu amigo sigue afuera."""
	me = UserFactory(username="me")
	stranger_insider = _insider("stranger")
	PinFactory(user=stranger_insider)

	resp = _auth(me).get(reverse("feed"), {"insider": "true"})

	assert _actors(resp) == set()
