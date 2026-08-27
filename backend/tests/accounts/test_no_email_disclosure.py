"""Ningún endpoint entrega el email de otra persona.

El email es el identificador con el que se busca a alguien en Muse, así que
entregarlo convierte cualquier listado en una libreta de direcciones. Y la
búsqueda por coincidencia parcial convertía a la plataforma en un directorio:
tres letras devolvían veinte personas con su dirección.
"""

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.models import Friendship
from tests.factories import PinFactory, UserFactory


def _auth(user):
	client = APIClient()
	client.force_authenticate(user=user)
	return client


def _named(username, email, display_name):
	user = UserFactory(username=username, email=email)
	user.profile.display_name = display_name
	user.profile.save()
	return user


# --- Búsqueda: sólo coincidencia exacta -------------------------------------


@pytest.mark.critical
@pytest.mark.django_db
def test_search_by_partial_name_finds_nobody():
	me = UserFactory(username="me", email="me@example.com")
	_named("ana", "ana@example.com", "Ana García")
	_named("mariana", "mariana@example.com", "Mariana López")

	resp = _auth(me).get(reverse("user_search"), {"q": "ana"})

	assert resp.json()["results"] == [], "un tipeo parcial no puede listar gente"


@pytest.mark.critical
@pytest.mark.django_db
def test_search_by_exact_email_still_works():
	me = UserFactory(username="me", email="me@example.com")
	target = _named("ana", "ana@example.com", "Ana García")

	resp = _auth(me).get(reverse("user_search"), {"q": "ana@example.com"})

	assert [row["id"] for row in resp.json()["results"]] == [target.id]


@pytest.mark.critical
@pytest.mark.django_db
def test_search_by_exact_phone_still_works():
	me = UserFactory(username="me", email="me@example.com")
	target = _named("ana", "ana@example.com", "Ana García")
	target.profile.phone = "+5491122334455"
	target.profile.save()

	resp = _auth(me).get(reverse("user_search"), {"q": "+5491122334455"})

	assert [row["id"] for row in resp.json()["results"]] == [target.id]


@pytest.mark.critical
@pytest.mark.django_db
def test_search_results_never_carry_an_email():
	me = UserFactory(username="me", email="me@example.com")
	target = _named("ana", "ana@example.com", "Ana García")

	resp = _auth(me).get(reverse("user_search"), {"q": target.email})

	assert target.email not in resp.content.decode()


# --- Amistades --------------------------------------------------------------


@pytest.mark.critical
@pytest.mark.django_db
def test_friendship_listings_never_carry_an_email():
	me = UserFactory(username="me", email="me@example.com")
	friend = _named("friend", "friend@example.com", "Amiga")
	stranger = _named("stranger", "stranger@example.com", "Desconocido")
	Friendship.objects.create(from_user=me, to_user=friend, status=Friendship.Status.ACCEPTED)
	Friendship.objects.create(from_user=stranger, to_user=me, status=Friendship.Status.PENDING)
	client = _auth(me)

	for url in (
		reverse("friendship-list"),
		reverse("friendship-friends"),
		reverse("friendship-requests"),
	):
		body = client.get(url).content.decode()
		assert friend.email not in body, url
		assert stranger.email not in body, url


@pytest.mark.critical
@pytest.mark.django_db
def test_creating_a_friend_request_does_not_echo_the_email():
	me = UserFactory(username="me", email="me@example.com")
	target = _named("target", "target@example.com", "Objetivo")

	resp = _auth(me).post(reverse("friendship-list"), {"toUserId": target.id}, format="json")

	assert resp.status_code == 201, resp.content
	assert target.email not in resp.content.decode()


# --- Feed -------------------------------------------------------------------


@pytest.mark.critical
@pytest.mark.django_db
def test_the_feed_never_carries_an_email():
	me = UserFactory(username="me", email="me@example.com")
	friend = _named("friend", "friend@example.com", "Amiga")
	Friendship.objects.create(from_user=me, to_user=friend, status=Friendship.Status.ACCEPTED)
	PinFactory(user=friend)

	body = _auth(me).get(reverse("feed")).content.decode()

	assert friend.email not in body


# --- Invitaciones -----------------------------------------------------------


@pytest.mark.critical
@pytest.mark.django_db
def test_inviting_someone_who_already_has_an_account_reveals_nothing():
	"""Decir "esta persona ya está en Muse" confirma que ese email tiene
	cuenta, a cualquiera que pruebe direcciones."""
	me = UserFactory(username="me", email="me@example.com")
	existing = _named("existing", "existing@example.com", "Ya está")
	client = _auth(me)

	on_muse = client.post(reverse("email_invite"), {"email": existing.email}, format="json")
	fresh = client.post(reverse("email_invite"), {"email": "nadie@example.com"}, format="json")

	assert (
		on_muse.status_code == fresh.status_code
	), f"distinguibles: en Muse={on_muse.status_code} nuevo={fresh.status_code}"
	assert "already" not in on_muse.content.decode().lower()
	assert "ya está" not in on_muse.content.decode().lower()
