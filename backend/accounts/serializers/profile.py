"""El perfil propio y el que ve un tercero.

`ForeignProfileSerializer` hereda del propio y **excluye** campos a mano: cada
campo nuevo del perfil aparece solo en el ajeno salvo que se lo agregue a
`_PRIVATE_PROFILE_FIELDS`. Esa clase de fuga ya pasó una vez, con los seis
campos de F2.E.
"""

import logging

from django.contrib.auth import get_user_model
from rest_framework import serializers

from accounts.models import (
	ConsentRecord,
	DietaryPreference,
	Profile,
)
from accounts.services.consent import client_ip, pending_policies, record_consent
from accounts.services.visibility import visible_pin_filter

User = get_user_model()

logger = logging.getLogger(__name__)


class DietaryPreferenceSerializer(serializers.ModelSerializer):
	class Meta:
		model = DietaryPreference
		fields = ("id", "name", "slug")


class ProfileSerializer(serializers.ModelSerializer):
	email = serializers.EmailField(source="user.email", read_only=True)
	stats = serializers.SerializerMethodField()
	pending_policies = serializers.SerializerMethodField()
	favourite_cuisine_detail = serializers.SerializerMethodField()
	dietary_preferences = serializers.PrimaryKeyRelatedField(
		queryset=DietaryPreference.objects.all(),
		many=True,
		required=False,
	)
	dietary_preferences_detail = DietaryPreferenceSerializer(
		source="dietary_preferences", many=True, read_only=True
	)

	class Meta:
		model = Profile
		fields = (
			"id",
			"email",
			"display_name",
			"bio",
			"avatar",
			"city",
			"website",
			"instagram",
			"phone",
			"favourite_cuisine",
			"favourite_cuisine_detail",
			"dietary_preferences",
			"dietary_preferences_detail",
			"analytics_opt_out",
			"default_pin_visibility",
			# F2.E. `language` y `timezone` los manda la app, no la persona: sin
			# ellos el push no sabe en qué idioma escribir ni a qué hora mandar
			# el resumen, porque lo inicia el servidor y no hay request del
			# destinatario de donde leerlos.
			"notify_friend_request",
			"notify_friend_accepted",
			"notify_daily_digest",
			"digest_prompt_seen",
			"pending_policies",
			"language",
			"timezone",
			"digest_hour",
			"is_verified_insider",
			"stats",
			"created_at",
		)
		# `is_verified_insider` es de sólo lectura o el badge no vale nada: lo
		# otorga Muse desde el admin, y un campo escribible acá lo convierte en
		# un PATCH que cualquiera manda sobre su propio perfil.
		read_only_fields = (
			"id",
			"email",
			"stats",
			"favourite_cuisine_detail",
			"dietary_preferences_detail",
			"is_verified_insider",
			"created_at",
		)

	def get_pending_policies(self, obj):
		"""Documentos legales que esta persona todavía no aceptó.

		Lista vacía es el caso normal. No vacía significa que la app tiene que
		pedirle que acepte antes de dejarla seguir: son las cuentas anteriores
		al registro de consentimientos, que nunca dejaron constancia de nada.
		"""
		return pending_policies(obj.user)

	def get_favourite_cuisine_detail(self, obj):
		if obj.favourite_cuisine:
			return {
				"id": obj.favourite_cuisine.id,
				"name": obj.favourite_cuisine.name,
				"slug": obj.favourite_cuisine.slug,
			}
		return None

	def get_stats(self, obj):
		user = obj.user
		# Los contadores cuentan lo que el viewer puede ver y no todo lo que
		# hay: un contador es cardinalidad, y "42 lugares" arriba de una lista
		# de 30 filtra que hay 12 escondidos. Sobre el perfil propio no cambia
		# nada, el dueño se ve todo lo suyo.
		pins = user.pins.filter(visible_pin_filter(self.context["request"].user))
		return {
			"pin_count": pins.count(),
			"visited_count": pins.filter(status="visited").count(),
			"to_visit_count": pins.filter(status="to_visit").count(),
			"friend_count": (
				user.friendships_sent.filter(status="accepted").count()
				+ user.friendships_received.filter(status="accepted").count()
			),
		}

	def update(self, instance, validated_data):
		"""Encender el resumen diario deja constancia; apagarlo no borra nada.

		No es una preferencia más: el consentimiento **es** la base legal con la
		que se manda, y hay que poder demostrar cuándo se dio. Se registra en la
		transición y no en cada PATCH que traiga el campo en True, porque la app
		manda el perfil entero y si no serían filas repetidas sin significado.

		Apagarlo tampoco borra la fila: es evidencia de lo que pasó, y lo que
		rige hoy lo dice `notify_daily_digest`.
		"""
		enciende_el_resumen = (
			validated_data.get("notify_daily_digest") is True and not instance.notify_daily_digest
		)
		profile = super().update(instance, validated_data)

		if enciende_el_resumen:
			record_consent(
				profile.user,
				ConsentRecord.Policy.DIGEST,
				ip_address=client_ip(self.context.get("request")),
			)

		return profile


# Lo que NO se entrega en el perfil de otra persona.
#
# Vive acá afuera porque el peligro de `ForeignProfileSerializer` es que crece
# por omisión: hereda los campos de `ProfileSerializer`, así que **cada campo
# nuevo del perfil propio aparece solo en el perfil ajeno** salvo que alguien
# se acuerde de excluirlo. Ya pasó con `email` y `phone`.
#
# Los de F2.E: `timezone` es una señal de ubicación (`Asia/Hong_Kong`) y junto
# con `digest_hour` le dice a cualquier amigo a qué hora exacta le suena el
# teléfono a otro. Las preferencias de notificación y el idioma son
# configuración privada: no hacen falta para dibujar el perfil de nadie.
_PRIVATE_PROFILE_FIELDS = (
	"email",
	"phone",
	"notify_friend_request",
	"notify_friend_accepted",
	"notify_daily_digest",
	"digest_prompt_seen",
	"pending_policies",
	"language",
	"timezone",
	"digest_hour",
)


class ForeignProfileSerializer(ProfileSerializer):
	"""El perfil de otra persona: lo mismo, menos los datos de contacto.

	`PublicProfileView` servía el `ProfileSerializer` entero, que trae `email`
	y `phone`. Su permiso —`require_can_view`— decide si podés mirar a esa
	persona, no qué campos suyos ves, así que cualquier amistad aceptada
	alcanzaba para leer la dirección y el teléfono de alguien. El invariante
	"ningún endpoint entrega el email de otra persona" ya estaba escrito y
	testeado para búsqueda, amistades, feed e invitaciones; a este endpoint no
	había llegado.

	El resto del payload se conserva tal cual: la pantalla de perfil ajeno
	muestra bio, ciudad, cocina, dietarias y stats, y recortar de más la
	rompe.
	"""

	class Meta(ProfileSerializer.Meta):
		fields = tuple(f for f in ProfileSerializer.Meta.fields if f not in _PRIVATE_PROFILE_FIELDS)
		read_only_fields = tuple(f for f in ProfileSerializer.Meta.read_only_fields if f != "email")
