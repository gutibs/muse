"""Las cuentas que nunca dejaron constancia de haber aceptado nada.

`ConsentRecord` llegó con una migración schema-only y sin backfill, así que las
cuentas anteriores quedaron sin ninguna fila: en producción, 16 de 17. Bajo
GDPR la carga de la prueba es del responsable, y para esas 16 no hay con qué
demostrar qué aceptaron ni cuándo.

La app las detecta con `pendingPolicies` y las manda a `POST /consent/`.
"""

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.models import ConsentRecord
from accounts.services.consent import LEGAL_POLICIES, POLICY_VERSIONS, pending_policies
from tests.factories import UserFactory

PASSWORD = "test-pass-123"


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
def test_una_cuenta_sin_registro_debe_todo():
	user = UserFactory(password=PASSWORD)

	assert set(pending_policies(user)) == set(LEGAL_POLICIES)


@pytest.mark.django_db
def test_quien_acepto_la_version_vigente_no_debe_nada():
	user = UserFactory(password=PASSWORD)
	for policy in LEGAL_POLICIES:
		ConsentRecord.objects.create(
			user=user, policy=policy, policy_version=POLICY_VERSIONS[policy]
		)

	assert pending_policies(user) == []


@pytest.mark.django_db
def test_una_aceptacion_vieja_no_cuenta():
	"""Al publicar un texto nuevo se bumpea la versión, y la firma anterior deja de valer."""
	user = UserFactory(password=PASSWORD)
	ConsentRecord.objects.create(
		user=user, policy=ConsentRecord.Policy.GDPR, policy_version="1999-01-01"
	)

	assert ConsentRecord.Policy.GDPR in pending_policies(user)


@pytest.mark.django_db
def test_el_endpoint_registra_lo_que_falta():
	user = UserFactory(password=PASSWORD)
	client = _auth_client(user)

	response = client.post(reverse("consent"), {}, format="json")

	assert response.status_code == 200, response.content
	assert set(response.json()["accepted"]) == set(LEGAL_POLICIES)
	assert pending_policies(user) == []
	# La versión queda estampada: sin eso no se sabe a qué texto dijo que sí.
	for registro in ConsentRecord.objects.filter(user=user):
		assert registro.policy_version == POLICY_VERSIONS[registro.policy]


@pytest.mark.django_db
def test_llamarlo_de_nuevo_no_duplica_la_evidencia():
	"""El cliente puede reintentar sin saber qué le falta: la view no puede castigarlo por eso."""
	user = UserFactory(password=PASSWORD)
	client = _auth_client(user)
	client.post(reverse("consent"), {}, format="json")

	response = client.post(reverse("consent"), {}, format="json")

	assert response.status_code == 200
	assert response.json()["accepted"] == []
	assert ConsentRecord.objects.filter(user=user).count() == len(LEGAL_POLICIES)


@pytest.mark.django_db
def test_el_perfil_dice_lo_que_falta():
	user = UserFactory(password=PASSWORD)
	client = _auth_client(user)

	cuerpo = client.get(reverse("profile")).json()

	assert set(cuerpo["pendingPolicies"]) == set(LEGAL_POLICIES)


@pytest.mark.django_db
def test_el_endpoint_exige_sesion():
	assert APIClient().post(reverse("consent"), {}, format="json").status_code == 401
