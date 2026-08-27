"""Las validaciones de `FriendshipSerializer`, que estaban escritas y muertas.

El campo de escritura se llama `to_user_id`, así que DRF busca
`validate_to_user_id`. El método existente se llamaba `validate_to_user` —el
nombre del campo de LECTURA— y por eso no corrió nunca: se podía mandar una
solicitud a uno mismo, y la duplicada reventaba con IntegrityError en vez de
dar 400.
"""

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.models import Friendship
from tests.factories import UserFactory


def _auth(user):
	client = APIClient()
	client.force_authenticate(user=user)
	return client


def _request_friendship(client, target):
	return client.post(reverse("friendship-list"), {"toUserId": target.id}, format="json")


@pytest.mark.critical
@pytest.mark.django_db
def test_cannot_send_a_friend_request_to_yourself():
	me = UserFactory()

	resp = _request_friendship(_auth(me), me)

	assert resp.status_code == 400, resp.content
	assert not Friendship.objects.exists()


@pytest.mark.critical
@pytest.mark.django_db
def test_a_duplicate_request_is_a_400_not_a_500():
	me, other = UserFactory(), UserFactory()
	client = _auth(me)
	assert _request_friendship(client, other).status_code == 201

	resp = _request_friendship(client, other)

	assert resp.status_code == 400, resp.content
	assert Friendship.objects.count() == 1


@pytest.mark.critical
@pytest.mark.django_db
def test_cannot_request_someone_who_already_requested_you():
	me, other = UserFactory(), UserFactory()
	Friendship.objects.create(from_user=other, to_user=me, status=Friendship.Status.PENDING)

	resp = _request_friendship(_auth(me), other)

	assert resp.status_code == 400, resp.content
	assert Friendship.objects.count() == 1
