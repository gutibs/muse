from rest_framework import serializers

from accounts.serializers import UserAnonymousSafeSerializer
from feed.models import Activity
from pins.serializers import PinSerializer


class ActivitySerializer(serializers.ModelSerializer):
	# También el actor va sin email. Es un amigo, así que sería defendible, pero
	# el feed no lo usa para nada y un identificador que no se muestra no tiene
	# por qué viajar.
	actor = UserAnonymousSafeSerializer(read_only=True)
	pin = PinSerializer(read_only=True)
	# Sin email a propósito: el `target_user` de una actividad de amistad es
	# alguien con quien el que mira no tiene ninguna relación —mi amigo se hizo
	# amigo de un desconocido— y `UserPublicSerializer` lleva el email. El feed
	# necesita el nombre para decir "X y Fulano ahora son amigos", nada más.
	target_user = UserAnonymousSafeSerializer(read_only=True)

	class Meta:
		model = Activity
		fields = ("id", "actor", "verb", "pin", "target_user", "created_at")
