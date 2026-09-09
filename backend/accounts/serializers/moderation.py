"""Bloquear y reportar (F2.B)."""

import logging

from django.contrib.auth import get_user_model
from rest_framework import serializers

from accounts.models import (
	Block,
	Report,
)
from accounts.serializers.social import UserAnonymousSafeSerializer
from pins.models import Pin

User = get_user_model()

logger = logging.getLogger(__name__)


class BlockSerializer(serializers.ModelSerializer):
	"""Un bloqueo, tal como lo ve quien lo hizo.

	Devuelve `user` (el bloqueado) y no `blocker`: este serializer sólo se usa
	para la lista propia, y quien la pide ya sabe que es él. Nunca se serializa
	un bloqueo recibido — eso le diría al bloqueado que lo bloquearon (RF2).
	"""

	# Sin email: se puede bloquear a CUALQUIERA por id, sin relación previa, así
	# que con UserPublicSerializer alcanzaba con recorrer ids —bloquear, leer,
	# desbloquear— para cosechar las direcciones de toda la base. Es la misma
	# fuga que se arregló en el feed; nada de la app usa este campo.
	user = UserAnonymousSafeSerializer(source="blocked", read_only=True)

	class Meta:
		model = Block
		fields = ("id", "user", "created_at")
		read_only_fields = fields


class ReportSerializer(serializers.ModelSerializer):
	"""Alta de una denuncia. Sólo escritura: nadie lista denuncias desde la app
	—ni el que reporta ni el reportado—, se resuelven en el admin.

	El queryset de `pin_id` se acota a los pins del usuario que se reporta.
	Con `Pin.objects.all()`, el error distinguía "ese pin no es de esa persona"
	de "ese pin no existe", y eso confirmaba pares (pin, dueño) de a uno —
	incluidos los `to_visit` de desconocidos, que ningún endpoint de lectura
	expone. Acotarlo hace que los dos casos den el mismo error de DRF.
	"""

	reported_user_id = serializers.PrimaryKeyRelatedField(
		queryset=User.objects.all(), source="reported_user", write_only=True
	)
	pin_id = serializers.PrimaryKeyRelatedField(
		queryset=Pin.objects.all(), source="pin", write_only=True, required=False, allow_null=True
	)

	class Meta:
		model = Report
		fields = ("id", "reported_user_id", "pin_id", "reason", "detail", "created_at")
		read_only_fields = ("id", "created_at")

	def validate(self, attrs):
		"""Acota el pin al dueño reportado antes de resolverlo.

		Se hace en `validate` y no en `__init__` porque el usuario reportado
		llega en el payload, no en el contexto. Como `pin_id` ya se resolvió
		contra `Pin.objects.all()`, acá se descarta el que no corresponde con
		el MISMO error que DRF da para un id inexistente.
		"""
		pin = attrs.get("pin")
		if pin is not None and pin.user_id != attrs["reported_user"].pk:
			raise serializers.ValidationError(
				{
					"pin_id": [
						serializers.PrimaryKeyRelatedField.default_error_messages[
							"does_not_exist"
						].format(pk_value=pin.pk)
					]
				}
			)
		return attrs


class BlockCreateSerializer(serializers.Serializer):
	"""Sólo valida la entrada de `POST /auth/blocks/`.

	Existe para que un `userId` ausente o no numérico dé 400 y no un 500: el
	`get_object_or_404` que había atrapa `DoesNotExist`, no el `ValueError` que
	tira el ORM cuando la pk no es un número.
	"""

	user_id = serializers.PrimaryKeyRelatedField(queryset=User.objects.all())
