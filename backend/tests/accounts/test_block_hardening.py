"""Lo que encontraron el code review y el security review sobre F2.B."""

import pytest
from django.contrib.admin.sites import site
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.models import Block, EmailInvitation, Friendship, Report
from accounts.serializers import RegisterSerializer
from accounts.services.visibility import visible_user_ids
from tests.factories import UserFactory


def _auth(user):
	client = APIClient()
	client.force_authenticate(user=user)
	return client


@pytest.mark.critical
@pytest.mark.django_db
def test_blocking_never_reveals_the_email_of_the_blocked_user():
	"""Se puede bloquear a cualquiera por id, sin relación previa, así que si
	la respuesta trae el email alcanza con recorrer ids para cosechar la base.
	Es la misma fuga que se arregló en el feed dos commits antes."""
	me = UserFactory()
	stranger = UserFactory(username="stranger", email="stranger-secret@example.com")

	created = _auth(me).post(reverse("block-list"), {"userId": stranger.id}, format="json")
	listed = _auth(me).get(reverse("block-list"))

	assert stranger.email not in created.content.decode()
	assert stranger.email not in listed.content.decode()


@pytest.mark.critical
@pytest.mark.django_db
def test_a_friend_request_to_a_blocker_looks_exactly_like_one_to_a_ghost():
	"""RF2. Si el rechazo por bloqueo se distingue del de un id inexistente,
	el acosador confirma que lo bloquearon — que es lo que RF2 evita."""
	me, blocker = UserFactory(), UserFactory()
	Block.objects.create(blocker=blocker, blocked=me)
	client = _auth(me)

	to_blocker = client.post(reverse("friendship-list"), {"toUserId": blocker.id}, format="json")
	to_ghost = client.post(reverse("friendship-list"), {"toUserId": 987654}, format="json")

	def _shape(resp, user_id):
		"""El id aparece en el mensaje, y es el que mandó el propio cliente:
		no es información del servidor. Se normaliza para comparar el resto."""
		return str(resp.json()).replace(str(user_id), "<id>")

	assert to_blocker.status_code == to_ghost.status_code == 400
	assert _shape(to_blocker, blocker.id) == _shape(
		to_ghost, 987654
	), f"distinguibles: bloqueado={to_blocker.json()} inexistente={to_ghost.json()}"


@pytest.mark.critical
@pytest.mark.django_db
def test_a_non_numeric_user_id_is_a_400_not_a_500():
	me = UserFactory()
	client = _auth(me)

	created = client.post(reverse("block-list"), {"userId": "abc"}, format="json")
	missing = client.post(reverse("block-list"), {}, format="json")

	assert created.status_code == 400, created.content
	assert missing.status_code == 400, missing.content


@pytest.mark.critical
@pytest.mark.django_db
def test_visible_user_ids_also_drops_blocked_people():
	"""Nadie la usa hoy, pero se llama "todos los usuarios cuyos datos puedo
	ver": la próxima superficie que la tome heredaría un bypass del bloqueo
	sin que ningún test se queje."""
	me, friend, blocked = UserFactory(), UserFactory(), UserFactory()
	Friendship.objects.create(from_user=me, to_user=friend, status=Friendship.Status.ACCEPTED)
	Friendship.objects.create(from_user=me, to_user=blocked, status=Friendship.Status.ACCEPTED)
	Block.objects.create(blocker=me, blocked=blocked)

	ids = visible_user_ids(me)

	assert blocked.id not in ids
	assert ids == {me.id, friend.id}


@pytest.mark.critical
@pytest.mark.django_db
def test_account_deletion_removes_blocks_in_both_directions():
	"""El contrato del módulo enumera lo que destruye. Un bloqueo es parte del
	grafo social, y sobre una cuenta que ya no puede entrar no protege nada."""
	from accounts.services.account_deletion import anonymise_user

	leaving, other, third = UserFactory(), UserFactory(), UserFactory()
	Block.objects.create(blocker=leaving, blocked=other)
	Block.objects.create(blocker=third, blocked=leaving)
	unrelated = Block.objects.create(blocker=other, blocked=third)

	anonymise_user(leaving)

	assert not Block.objects.filter(blocker=leaving).exists()
	assert not Block.objects.filter(blocked=leaving).exists()
	assert Block.objects.filter(pk=unrelated.pk).exists(), "los ajenos no se tocan"


@pytest.mark.critical
@pytest.mark.django_db
def test_the_invite_path_skips_a_blocked_inviter():
	"""D-005 crea una amistad ACCEPTED sola al registrarse con un email
	invitado, sin acto de quien se registra. La guarda comprueba el bloqueo
	antes de crearla.

	NO hay hoy un camino de producto que llegue a este estado: para que exista
	un bloqueo hace falta una cuenta, y con cuenta ya no te registrás. El
	borrado de cuenta tampoco lo abre —se lleva el bloqueo y las invitaciones
	dirigidas a ese email—. Se deja igual porque son dos líneas, el invariante
	("un bloqueo no se revierte solo") es del tipo que se rompe en silencio, y
	basta con que alguien agregue "cambiar mi email" para volverlo alcanzable.
	Se testea la guarda directamente, ya que el flujo no puede producirla.
	"""
	from accounts.serializers import RegisterSerializer

	inviter, invitee = UserFactory(), UserFactory()
	Block.objects.create(blocker=inviter, blocked=invitee)
	EmailInvitation.objects.create(from_user=inviter, email=invitee.email, accepted=False)

	RegisterSerializer()._consume_invitations(invitee)

	assert not Friendship.objects.exists(), "el bloqueo tiene que ganarle a D-005"


@pytest.mark.critical
@pytest.mark.django_db
def test_the_invite_path_still_creates_the_friendship_without_a_block():
	inviter, invitee = UserFactory(), UserFactory()
	EmailInvitation.objects.create(from_user=inviter, email=invitee.email, accepted=False)

	RegisterSerializer()._consume_invitations(invitee)

	assert Friendship.objects.filter(
		from_user=inviter, to_user=invitee, status=Friendship.Status.ACCEPTED
	).exists()


@pytest.mark.critical
@pytest.mark.django_db
def test_moderation_evidence_cannot_be_deleted_from_the_admin():
	"""Una denuncia se cierra por status, no borrándola: la fila es la
	constancia de que se actuó. Y desbloquear es del dueño del bloqueo."""
	for model in (Block, Report):
		model_admin = site._registry[model]
		assert model_admin.has_delete_permission(None) is False, model.__name__


@pytest.mark.critical
@pytest.mark.django_db
def test_report_throttle_counts_per_user_not_per_ip(settings):
	"""El endpoint es autenticado: contar por IP deja que un abusador detrás
	de un NAT le agote el cupo a todos los demás, y reportar es justamente la
	capacidad que la guideline exige que funcione."""
	from rest_framework.throttling import UserRateThrottle

	from accounts.views import ReportThrottle

	assert issubclass(ReportThrottle, UserRateThrottle)
