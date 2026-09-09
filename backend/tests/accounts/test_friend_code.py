"""F2.F — el código de amistad que viaja en el QR.

El seam es el endpoint: los tests entran por donde entra la app. Lo que se
protege acá no es "crear una Friendship" —eso ya lo hace el flujo de
siempre— sino las decisiones de privacidad del canje, que viven en los
status codes: quién puede saber que un código existe y quién no.
"""

import uuid

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.models import Block, Friendship
from notifications.models import NotificationJob
from tests.factories import UserFactory


def _auth(user):
	client = APIClient()
	client.force_authenticate(user=user)
	return client


def _redeem(client, code):
	return client.post(reverse("friend-code-redeem"), {"code": str(code)}, format="json")


@pytest.mark.critical
@pytest.mark.django_db
def test_canjear_un_codigo_valido_crea_una_solicitud_pendiente():
	quien_escanea, dueño = UserFactory(), UserFactory()

	res = _redeem(_auth(quien_escanea), dueño.profile.friend_code)

	assert res.status_code == 201
	amistad = Friendship.objects.get(from_user=quien_escanea, to_user=dueño)
	assert amistad.status == Friendship.Status.PENDING


@pytest.mark.critical
@pytest.mark.django_db
def test_canjear_el_codigo_propio_no_crea_nada():
	yo = UserFactory()

	res = _redeem(_auth(yo), yo.profile.friend_code)

	assert res.status_code == 400
	assert not Friendship.objects.exists()


@pytest.mark.critical
@pytest.mark.django_db
def test_un_codigo_que_no_existe_da_404():
	res = _redeem(_auth(UserFactory()), uuid.uuid4())

	assert res.status_code == 404


@pytest.mark.critical
@pytest.mark.django_db
def test_un_codigo_ilegible_da_404_y_no_un_500():
	"""El campo es `uuid`: un string cualquiera reventaría la query."""
	res = _redeem(_auth(UserFactory()), "no-soy-un-uuid")

	assert res.status_code == 404


@pytest.mark.critical
@pytest.mark.django_db
def test_el_codigo_de_alguien_que_me_bloqueo_da_el_mismo_404_que_uno_inexistente():
	"""El bloqueo es silencioso: un 403 le confirmaría al bloqueado que existe."""
	quien_escanea, dueño = UserFactory(), UserFactory()
	Block.objects.create(blocker=dueño, blocked=quien_escanea)

	res = _redeem(_auth(quien_escanea), dueño.profile.friend_code)

	assert res.status_code == 404
	assert not Friendship.objects.exists()


@pytest.mark.critical
@pytest.mark.django_db
def test_el_codigo_de_alguien_a_quien_bloquee_tampoco_se_canjea():
	quien_escanea, dueño = UserFactory(), UserFactory()
	Block.objects.create(blocker=quien_escanea, blocked=dueño)

	res = _redeem(_auth(quien_escanea), dueño.profile.friend_code)

	assert res.status_code == 404
	assert not Friendship.objects.exists()


@pytest.mark.critical
@pytest.mark.django_db
def test_canjear_dos_veces_el_mismo_codigo_no_duplica_la_solicitud():
	"""`Friendship` tiene unique_together: sin esto el segundo POST es un 500."""
	quien_escanea, dueño = UserFactory(), UserFactory()
	client = _auth(quien_escanea)

	primera = _redeem(client, dueño.profile.friend_code)
	segunda = _redeem(client, dueño.profile.friend_code)

	assert primera.status_code == 201
	assert segunda.status_code == 200
	assert Friendship.objects.count() == 1


@pytest.mark.critical
@pytest.mark.django_db
def test_canjear_el_codigo_de_alguien_que_ya_es_amigo_no_toca_la_amistad():
	quien_escanea, dueño = UserFactory(), UserFactory()
	Friendship.objects.create(
		from_user=dueño, to_user=quien_escanea, status=Friendship.Status.ACCEPTED
	)

	res = _redeem(_auth(quien_escanea), dueño.profile.friend_code)

	assert res.status_code == 200
	assert Friendship.objects.count() == 1
	assert Friendship.objects.get().status == Friendship.Status.ACCEPTED


@pytest.mark.critical
@pytest.mark.django_db
def test_mi_perfil_trae_mi_codigo():
	yo = UserFactory()

	res = _auth(yo).get(reverse("profile"))

	assert res.status_code == 200
	assert res.json()["friendCode"] == str(yo.profile.friend_code)


@pytest.mark.critical
@pytest.mark.django_db
def test_el_perfil_de_otro_no_trae_su_codigo():
	"""`ForeignProfileSerializer` hereda de `ProfileSerializer`: todo campo
	nuevo aparece en el perfil ajeno salvo que se lo excluya. Ya pasó con
	`email`, `phone` y los seis de F2.E."""
	yo, amigo = UserFactory(), UserFactory()
	Friendship.objects.create(from_user=yo, to_user=amigo, status=Friendship.Status.ACCEPTED)

	res = _auth(yo).get(reverse("public_profile", args=[amigo.id]))

	assert res.status_code == 200
	assert "friendCode" not in res.json()


@pytest.mark.critical
@pytest.mark.django_db
def test_rotar_el_codigo_invalida_el_anterior():
	dueño = UserFactory()
	viejo = dueño.profile.friend_code

	res = _auth(dueño).post(reverse("friend-code-rotate"))

	assert res.status_code == 200
	dueño.profile.refresh_from_db()
	assert dueño.profile.friend_code != viejo
	assert res.json()["friendCode"] == str(dueño.profile.friend_code)
	# Y el viejo ya no sirve para nadie.
	assert _redeem(_auth(UserFactory()), viejo).status_code == 404


@pytest.mark.critical
@pytest.mark.django_db
def test_el_codigo_no_se_puede_elegir_a_mano():
	"""Si fuera escribible, cualquiera se pondría uno adivinable."""
	yo = UserFactory()
	original = yo.profile.friend_code
	elegido = uuid.uuid4()

	res = _auth(yo).patch(reverse("profile"), {"friendCode": str(elegido)}, format="json")

	assert res.status_code == 200
	yo.profile.refresh_from_db()
	assert yo.profile.friend_code == original


@pytest.mark.critical
@pytest.mark.django_db
def test_el_canje_tiene_su_propio_rate_limit(rates_de_produccion):
	"""Sin scope propio, probar códigos al voleo cuesta lo mismo que cualquier
	request autenticada (1000/hora)."""
	rates_de_produccion(friend_code="3/hour")
	client = _auth(UserFactory())

	codigos = [uuid.uuid4() for _ in range(4)]
	respuestas = [_redeem(client, c).status_code for c in codigos]

	assert respuestas[:3] == [404, 404, 404]
	assert respuestas[3] == 429


@pytest.mark.critical
@pytest.mark.django_db
def test_cada_perfil_recibe_un_codigo_distinto():
	"""El default tiene que ser el callable, no su resultado: escribir
	`default=uuid.uuid4()` —con paréntesis— congela un único valor para toda
	la tabla, y con `unique=True` el segundo alta explota."""
	perfiles = [UserFactory().profile for _ in range(3)]

	codigos = {p.friend_code for p in perfiles}
	assert len(codigos) == 3
	assert all(c is not None for c in codigos)


@pytest.mark.critical
@pytest.mark.django_db(transaction=True)
def test_canjear_un_codigo_le_avisa_al_dueño():
	"""La notificación cuelga de un `post_save` con `on_commit`, no de la
	view: si el canje dejara de crear la fila por el camino normal, el dueño
	no se enteraría de la solicitud."""
	quien_escanea, dueño = UserFactory(), UserFactory()

	_redeem(_auth(quien_escanea), dueño.profile.friend_code)

	job = NotificationJob.objects.get(recipient=dueño)
	assert job.kind == NotificationJob.Kind.FRIENDSHIP_REQUEST
	assert job.context["actor_id"] == quien_escanea.id


@pytest.mark.critical
@pytest.mark.django_db
def test_el_canje_devuelve_a_quien_le_mandaste_la_solicitud_sin_su_email():
	quien_escanea, dueño = UserFactory(), UserFactory()
	dueño.profile.display_name = "Jess"
	dueño.profile.save(update_fields=["display_name"])

	body = _redeem(_auth(quien_escanea), dueño.profile.friend_code).json()

	assert body["user"]["displayName"] == "Jess"
	assert body["status"] == "pending"
	assert "email" not in body["user"]
