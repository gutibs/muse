"""RF1-RF8 — bloquear, desbloquear y listar.

Los tres casos que el pase adversarial marcó como críticos están acá: el
segundo POST (idempotencia real, no `IntegrityError`), las `Activity` de
amistad que quedaban huérfanas, y aceptar una solicitud después del bloqueo.
"""

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.models import Block, Friendship
from feed.models import Activity
from tests.factories import UserFactory


def _auth(user):
	client = APIClient()
	client.force_authenticate(user=user)
	return client


def _befriend(a, b):
	return Friendship.objects.create(from_user=a, to_user=b, status=Friendship.Status.ACCEPTED)


def _block(client, user):
	return client.post(reverse("block-list"), {"userId": user.id}, format="json")


@pytest.mark.critical
@pytest.mark.django_db
def test_blocking_creates_one_row():
	me, other = UserFactory(), UserFactory()

	resp = _block(_auth(me), other)

	assert resp.status_code in (200, 201), resp.content
	assert Block.objects.filter(blocker=me, blocked=other).count() == 1


@pytest.mark.critical
@pytest.mark.django_db
def test_blocking_twice_is_idempotent():
	"""`unique_together` solo daría IntegrityError → 500. El segundo POST tiene
	que contestar bien y dejar una sola fila."""
	me, other = UserFactory(), UserFactory()
	client = _auth(me)

	first = _block(client, other)
	second = _block(client, other)

	assert first.status_code in (200, 201), first.content
	assert second.status_code in (200, 201), second.content
	assert Block.objects.filter(blocker=me, blocked=other).count() == 1


@pytest.mark.critical
@pytest.mark.django_db
def test_blocking_yourself_is_rejected():
	"""`are_friends(a, a)` devuelve True sin tocar la base: un self-block
	escondería los datos propios."""
	me = UserFactory()

	resp = _block(_auth(me), me)

	assert resp.status_code == 400, resp.content
	assert Block.objects.count() == 0


@pytest.mark.critical
@pytest.mark.django_db
def test_blocking_destroys_the_friendship_and_its_activities():
	"""RF3. Sin borrar las Activity, un tercero amigo de los dos sigue viendo
	'A y B ahora son amigos' para una amistad que ya no existe."""
	me, other, witness = UserFactory(), UserFactory(), UserFactory()
	_befriend(me, other)
	_befriend(witness, me)
	_befriend(witness, other)
	assert Activity.objects.filter(verb=Activity.Verb.FRIENDSHIP).exists()

	_block(_auth(me), other)

	assert not Friendship.objects.filter(from_user=me, to_user=other).exists()
	assert not Friendship.objects.filter(from_user=other, to_user=me).exists()
	pair = Activity.objects.filter(
		verb=Activity.Verb.FRIENDSHIP, actor__in=[me, other], target_user__in=[me, other]
	)
	assert not pair.exists(), "quedaron actividades de una amistad que ya no existe"
	# Las de terceros con cada uno siguen intactas.
	assert Activity.objects.filter(verb=Activity.Verb.FRIENDSHIP, actor=witness).exists()


@pytest.mark.critical
@pytest.mark.django_db
def test_blocking_kills_a_pending_request():
	me, other = UserFactory(), UserFactory()
	Friendship.objects.create(from_user=other, to_user=me, status=Friendship.Status.PENDING)

	_block(_auth(me), other)

	assert not Friendship.objects.filter(from_user=other, to_user=me).exists()
	assert _auth(me).get(reverse("friendship-requests")).json() == []


@pytest.mark.critical
@pytest.mark.django_db
def test_a_blocked_user_cannot_send_a_friend_request():
	"""Y el error no dice que hay un bloqueo (RF2)."""
	me, other = UserFactory(), UserFactory()
	_block(_auth(me), other)

	resp = _auth(other).post(reverse("friendship-list"), {"toUserId": me.id}, format="json")

	assert resp.status_code == 400, resp.content
	# Que no pase por "campo requerido": el payload es válido, lo que lo
	# rechaza es el bloqueo.
	assert "toUserId" not in resp.json() or "requer" not in str(resp.json()).lower()
	assert "block" not in resp.content.decode().lower()
	assert "bloque" not in resp.content.decode().lower()
	assert not Friendship.objects.exists()


@pytest.mark.critical
@pytest.mark.django_db
def test_accepting_a_request_after_being_blocked_fails():
	"""La carrera: A bloquea mientras B tiene la pantalla abierta y acepta."""
	me, other = UserFactory(), UserFactory()
	friendship = Friendship.objects.create(
		from_user=me, to_user=other, status=Friendship.Status.PENDING
	)
	Block.objects.create(blocker=me, blocked=other)

	resp = _auth(other).patch(
		reverse("friendship-detail", kwargs={"pk": friendship.pk}),
		{"status": "accepted"},
		format="json",
	)

	assert resp.status_code == 400, resp.content
	friendship.refresh_from_db()
	assert friendship.status != Friendship.Status.ACCEPTED


@pytest.mark.critical
@pytest.mark.django_db
def test_unblocking_removes_the_row_but_not_the_friendship():
	me, other = UserFactory(), UserFactory()
	_befriend(me, other)
	client = _auth(me)
	_block(client, other)

	resp = client.delete(reverse("block-detail", kwargs={"blocked_id": other.id}))

	assert resp.status_code == 204, resp.content
	assert not Block.objects.exists()
	assert not Friendship.objects.exists(), "desbloquear no revive la amistad (RF4)"


@pytest.mark.critical
@pytest.mark.django_db
def test_listing_shows_only_the_blocks_i_made():
	"""RF8: si devolviera los bloqueos recibidos, el bloqueado se enteraría."""
	me, blocked_by_me, blocker_of_me = UserFactory(), UserFactory(), UserFactory()
	Block.objects.create(blocker=me, blocked=blocked_by_me)
	Block.objects.create(blocker=blocker_of_me, blocked=me)

	resp = _auth(me).get(reverse("block-list"))

	assert resp.status_code == 200, resp.content
	ids = [row["user"]["id"] for row in resp.json()]
	assert ids == [blocked_by_me.id]


@pytest.mark.critical
@pytest.mark.django_db
def test_blocking_requires_authentication():
	other = UserFactory()

	resp = APIClient().post(reverse("block-list"), {"userId": other.id}, format="json")

	assert resp.status_code == 401
