"""El resumen diario se pide, no viene puesto.

Hasta el 2026-09-08 `notify_daily_digest` arrancaba en True y el alta no
pregunta nada sobre notificaciones, así que los 17 perfiles de producción lo
tenían encendido sin haberlo visto nunca. Es actividad de terceros empujada al
teléfono —no algo que pasó con tu cuenta—, así que la base legal es el
consentimiento, y un default no es consentimiento.

Lo que fijan estos tests: que nazca apagado, que encenderlo deje evidencia
demostrable, y que la migración no le haya apagado el resumen a quien sí lo
había pedido.
"""

import importlib

import pytest
from django.apps import apps as django_apps
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.models import ConsentRecord, Friendship, Profile
from accounts.serializers.profile import _PRIVATE_PROFILE_FIELDS
from accounts.services.consent import POLICY_VERSIONS
from tests.factories import FriendshipFactory, UserFactory

PASSWORD = "test-pass-123"

MIGRACION = importlib.import_module("accounts.migrations.0020_apagar_el_resumen_que_nadie_eligio")


def _auth_client(user):
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


@pytest.mark.django_db
def test_un_perfil_nuevo_nace_sin_el_resumen():
	user = UserFactory(password=PASSWORD)

	assert user.profile.notify_daily_digest is False
	# Las dirigidas a la persona sí siguen encendidas: son transaccionales.
	assert user.profile.notify_friend_request is True
	assert user.profile.notify_friend_accepted is True


@pytest.mark.django_db
def test_encender_el_resumen_deja_constancia():
	user = UserFactory(password=PASSWORD)
	client = _auth_client(user)

	response = client.patch(reverse("profile"), {"notifyDailyDigest": True}, format="json")

	assert response.status_code == 200, response.content
	consent = ConsentRecord.objects.get(user=user, policy=ConsentRecord.Policy.DIGEST)
	# La versión importa tanto como la fecha: hay que poder decir a qué texto
	# dijo que sí.
	assert consent.policy_version == POLICY_VERSIONS[ConsentRecord.Policy.DIGEST]
	assert consent.accepted_at is not None


@pytest.mark.django_db
def test_pedirlo_de_nuevo_no_multiplica_la_evidencia():
	"""La app manda el perfil entero: sin mirar la transición, cada PATCH sumaría una fila."""
	user = UserFactory(password=PASSWORD)
	client = _auth_client(user)

	client.patch(reverse("profile"), {"notifyDailyDigest": True}, format="json")
	client.patch(reverse("profile"), {"notifyDailyDigest": True}, format="json")
	client.patch(reverse("profile"), {"digestHour": 9}, format="json")

	assert ConsentRecord.objects.filter(policy=ConsentRecord.Policy.DIGEST).count() == 1


@pytest.mark.django_db
def test_apagarlo_no_borra_lo_que_ya_paso():
	"""El consentimiento es evidencia de un hecho; lo que rige hoy es la preferencia."""
	user = UserFactory(password=PASSWORD)
	client = _auth_client(user)
	client.patch(reverse("profile"), {"notifyDailyDigest": True}, format="json")

	client.patch(reverse("profile"), {"notifyDailyDigest": False}, format="json")

	assert Profile.objects.get(user=user).notify_daily_digest is False
	assert ConsentRecord.objects.filter(policy=ConsentRecord.Policy.DIGEST).exists()


@pytest.mark.django_db
def test_la_migracion_apaga_el_resumen_que_nadie_pidio():
	user = UserFactory(password=PASSWORD)
	Profile.objects.filter(user=user).update(notify_daily_digest=True, digest_prompt_seen=True)

	MIGRACION.apagar_el_resumen(django_apps, None)

	perfil = Profile.objects.get(user=user)
	assert perfil.notify_daily_digest is False
	# Y vuelve a quedar pendiente de preguntar: si no, el resumen les
	# desaparece sin que nadie les diga nada.
	assert perfil.digest_prompt_seen is False


@pytest.mark.django_db
def test_la_migracion_no_toca_a_quien_si_lo_pidio():
	user = UserFactory(password=PASSWORD)
	Profile.objects.filter(user=user).update(notify_daily_digest=True)
	ConsentRecord.objects.create(
		user=user,
		policy=ConsentRecord.Policy.DIGEST,
		policy_version=POLICY_VERSIONS[ConsentRecord.Policy.DIGEST],
	)

	MIGRACION.apagar_el_resumen(django_apps, None)

	assert Profile.objects.get(user=user).notify_daily_digest is True


@pytest.mark.django_db
def test_ningun_campo_privado_viaja_en_el_perfil_de_otro():
	"""El guardián de la clase de bug que la revisión de F2.E encontró.

	`ForeignProfileSerializer` hereda los campos del propio, así que cada campo
	nuevo aparece solo en el ajeno salvo que se lo excluya. Recorrer la lista
	entera evita que el próximo campo dependa de que alguien se acuerde.
	"""
	yo = UserFactory(password=PASSWORD)
	otro = UserFactory()
	# El perfil ajeno sólo se sirve entre amigos, así que la fuga sólo puede
	# darse acá: es exactamente donde hay que mirar.
	FriendshipFactory(from_user=yo, to_user=otro, status=Friendship.Status.ACCEPTED)
	client = _auth_client(yo)

	response = client.get(reverse("public_profile", args=[otro.id]))

	assert response.status_code == 200, response.content
	cuerpo = response.json()
	filtrados = [campo for campo in _PRIVATE_PROFILE_FIELDS if _camel(campo) in cuerpo]
	assert not filtrados, f"campos privados servidos en el perfil ajeno: {filtrados}"


def _camel(snake: str) -> str:
	cabeza, *resto = snake.split("_")
	return cabeza + "".join(p.title() for p in resto)
