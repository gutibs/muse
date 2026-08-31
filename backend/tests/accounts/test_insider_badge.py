"""F1.7 — el badge de Verified Insider: quién lo otorga y dónde se ve.

La marca la da Muse a mano desde el admin, y lo único que puede vaciarla de
significado en silencio es que el campo entre por el serializer del perfil:
ahí cualquiera se auto-verifica con un PATCH y el badge deja de decir nada.
Ese es el test que el plan declara obligatorio.
"""

import pytest
from django.contrib.admin.sites import site
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.models import Profile
from tests.factories import UserFactory


def _auth(user):
	client = APIClient()
	client.force_authenticate(user=user)
	return client


def _insider(username="insider"):
	user = UserFactory(username=username)
	user.profile.is_verified_insider = True
	user.profile.save()
	return user


# --- Nadie se verifica solo -------------------------------------------------


@pytest.mark.critical
@pytest.mark.django_db
def test_patching_the_profile_cannot_grant_the_badge():
	user = UserFactory()

	resp = _auth(user).patch(reverse("profile"), {"isVerifiedInsider": True}, format="json")

	assert resp.status_code == 200
	user.profile.refresh_from_db()
	assert (
		user.profile.is_verified_insider is False
	), "el badge entró por el serializer: cualquiera se verifica con un PATCH"


@pytest.mark.critical
@pytest.mark.django_db
def test_the_field_is_declared_read_only():
	"""El invariante de arriba, dicho sobre el serializer mismo.

	El test de comportamiento pasa también si alguien saca el campo de
	`fields`; éste falla si lo devuelven a escritura.
	"""
	from accounts.serializers import ProfileSerializer

	assert "is_verified_insider" in ProfileSerializer.Meta.fields
	assert "is_verified_insider" in ProfileSerializer.Meta.read_only_fields


# --- La persona ve su propio badge ------------------------------------------


@pytest.mark.django_db
def test_the_owner_sees_the_badge_on_their_own_profile():
	user = _insider()

	resp = _auth(user).get(reverse("profile"))

	assert resp.json()["isVerifiedInsider"] is True


@pytest.mark.django_db
def test_a_plain_account_is_not_an_insider():
	user = UserFactory()

	resp = _auth(user).get(reverse("profile"))

	assert resp.json()["isVerifiedInsider"] is False


# --- El badge viaja a terceros ----------------------------------------------


@pytest.mark.django_db
def test_the_badge_travels_in_user_search():
	"""El serializer anónimo es el punto único: si sale acá, sale en las seis."""
	me = UserFactory(username="me", email="me@example.com")
	target = _insider("ana")
	target.email = "ana@example.com"
	target.save()

	resp = _auth(me).get(reverse("user_search"), {"q": "ana@example.com"})

	assert resp.json()["results"][0]["isVerifiedInsider"] is True


# --- El admin es donde se otorga y se quita ---------------------------------


@pytest.mark.critical
@pytest.mark.django_db
def test_the_badge_can_be_granted_from_the_profile_list():
	"""Sin `list_editable` hay que abrir la ficha de cada persona."""
	model_admin = site._registry[Profile]

	assert "is_verified_insider" in model_admin.list_display
	assert "is_verified_insider" in model_admin.list_editable
	assert "is_verified_insider" in model_admin.list_filter


@pytest.mark.critical
@pytest.mark.django_db
def test_the_bulk_actions_grant_and_revoke():
	model_admin = site._registry[Profile]
	granted, revoked = UserFactory(username="a"), _insider("b")
	request = _admin_request()

	qs = Profile.objects.filter(user__in=[granted, revoked])
	model_admin.grant_insider(request, qs)

	granted.profile.refresh_from_db()
	revoked.profile.refresh_from_db()
	assert granted.profile.is_verified_insider is True
	assert revoked.profile.is_verified_insider is True

	model_admin.revoke_insider(request, qs)

	granted.profile.refresh_from_db()
	revoked.profile.refresh_from_db()
	assert granted.profile.is_verified_insider is False
	assert revoked.profile.is_verified_insider is False


def _admin_request():
	"""Un request con lo mínimo que necesitan `message_user` y el log."""
	from django.contrib.messages.storage.fallback import FallbackStorage
	from django.test import RequestFactory

	request = RequestFactory().post("/admin/accounts/profile/")
	request.user = UserFactory(username="staff", is_staff=True, is_superuser=True)
	request.session = {}
	request._messages = FallbackStorage(request)
	return request


# --- Borrar la cuenta se lleva el badge -------------------------------------


@pytest.mark.critical
@pytest.mark.django_db
def test_erasing_an_account_removes_the_badge():
	"""El badge es identidad, y el borrado promete destruir la identidad.

	Sin esto la reseña sobreviviente queda firmada como "Anónimo" con la
	marca de Muse al lado, y la cuenta sigue contando en el filtro de
	Insiders.
	"""
	from accounts.services.account_deletion import anonymise_user

	user = _insider()

	anonymise_user(user)

	user.profile.refresh_from_db()
	assert user.profile.is_verified_insider is False
