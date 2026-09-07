from rest_framework import serializers

from notifications.models import DeviceToken


class DeviceTokenSerializer(serializers.Serializer):
	"""Serializer plano y no un ModelSerializer a propósito.

	Sobre el modelo, DRF hereda el `UniqueValidator` de `token` y devuelve 400
	cuando el mismo dispositivo se registra dos veces — que es el caso normal,
	porque la app registra al iniciar sesión y cada vez que FCM rota el token.
	El endpoint tiene que ser idempotente; la unicidad la resuelve el
	`update_or_create` de la vista, que además mueve la fila de dueño.
	"""

	token = serializers.CharField(max_length=255)
	platform = serializers.ChoiceField(
		choices=DeviceToken.Platform.choices,
		default=DeviceToken.Platform.ANDROID,
	)
