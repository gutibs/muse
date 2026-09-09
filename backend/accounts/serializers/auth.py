"""Alta, contraseña y baja de cuenta.

Todo lo que decide quién entra y quién deja de existir. `RegisterSerializer`
no revela si un email ya estaba registrado: manda un correo distinto y contesta
lo mismo en los dos casos.
"""

import logging

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from accounts.models import (
	ConsentRecord,
	EmailInvitation,
	Friendship,
)
from accounts.services.blocking import is_blocked
from accounts.services.consent import client_ip, record_consent
from accounts.services.email import (
	EmailSendError,
	send_account_exists_email,
	send_welcome_email,
)

User = get_user_model()

logger = logging.getLogger(__name__)


class RegisterSerializer(serializers.Serializer):
	# Un solo cuerpo para los dos caminos: si el texto difiere, aunque sea en
	# un espacio, vuelve el oráculo.
	CONFIRMATION_DETAIL = _("Check your inbox to finish setting up your account.")

	email = serializers.EmailField()
	password = serializers.CharField(write_only=True, validators=[validate_password])
	display_name = serializers.CharField(max_length=100, required=False, default="")
	# Active consent: a single unified privacy checkbox, required and must be
	# explicitly True. A missing or False value is a 400 — the client cannot
	# register without ticking it. Accepting the unified policy still persists
	# one ConsentRecord per framework (GDPR + PDPO) as legal proof.
	accept_privacy = serializers.BooleanField(write_only=True)

	def validate_email(self, value):
		# No se rechaza el email ya tomado: hacerlo le decía a cualquiera, un
		# email por vez, quién tiene cuenta en Muse. El caso se resuelve en
		# `create`, que responde igual y le avisa al dueño de la casilla.
		return value.lower()

	def validate_accept_privacy(self, value):
		# El campo se sigue llamando `accept_privacy` a propósito: hay APKs
		# publicados que mandan `acceptPrivacy` y renombrarlo los rompe. Lo que
		# cambia es qué cubre, que ahora incluye los términos.
		if value is not True:
			raise serializers.ValidationError(
				_("You must accept the privacy policy and the terms to register.")
			)
		return value

	def _consume_invitations(self, user):
		"""Convierte en amistad las invitaciones dirigidas al email de `user`.

		ACCEPTED y no PENDING: el mail de invitación promete que la amistad se
		crea sola, y registrarse por ahí es el consentimiento. Ver D-005.
		"""
		invitations = EmailInvitation.objects.filter(
			email__iexact=user.email,
			accepted=False,
		)
		for invitation in invitations:
			# La amistad se crea sin acto de quien se registra, así que un
			# bloqueo se revertiría solo por este camino. Hoy no hay forma de
			# llegar acá —para tener un bloqueo hace falta una cuenta, y con
			# cuenta no te registrás—, pero el invariante "un bloqueo no se
			# revierte solo" se rompe en silencio, y alcanza con que exista un
			# "cambiar mi email" para volverlo alcanzable.
			if is_blocked(invitation.from_user, user):
				continue
			Friendship.objects.create(
				from_user=invitation.from_user,
				to_user=user,
				status=Friendship.Status.ACCEPTED,
			)
			invitation.accepted = True
			invitation.save(update_fields=["accepted"])

	@staticmethod
	def _notify(send, **kwargs):
		"""El mail no puede tumbar el alta: perder la cuenta porque Resend está
		caído es peor que no mandar la confirmación."""
		try:
			send(**kwargs)
		except EmailSendError as exc:
			logger.error("Account email not sent (status=%s): %s", exc.status_code, exc.message)

	def create(self, validated_data):
		"""Da de alta la cuenta, o avisa al dueño si el email ya está tomado.

		Los dos caminos devuelven exactamente lo mismo y ninguno devuelve
		sesión. Ésa es la razón de que el alta ya no loguee: con tokens en la
		respuesta, el caso del email tomado no podía ser idéntico sin entregar
		esa cuenta.
		"""
		language = self.context["request"].data.get("language")
		existing = User.objects.filter(email__iexact=validated_data["email"]).first()
		if existing is not None:
			# No se toca nada de esa cuenta. El único efecto es el aviso, que va
			# a la casilla: quien probó no se entera de nada.
			self._notify(send_account_exists_email, to_email=existing.email, language=language)
			return {"detail": self.CONFIRMATION_DETAIL}

		user = User.objects.create_user(
			username=validated_data["email"],
			email=validated_data["email"],
			password=validated_data["password"],
		)
		if validated_data.get("display_name"):
			user.profile.display_name = validated_data["display_name"]
			user.profile.save(update_fields=["display_name"])

		# Las tres con un solo checkbox: los dos marcos legales que aplican
		# según dónde esté la persona, y los términos, que hasta ahora se
		# mostraban como texto debajo del botón sin que nadie los aceptara ni
		# quedara constancia de nada.
		record_consent(
			user,
			[
				ConsentRecord.Policy.GDPR,
				ConsentRecord.Policy.PDPO,
				ConsentRecord.Policy.TERMS,
			],
			ip_address=client_ip(self.context.get("request")),
		)

		self._consume_invitations(user)
		self._notify(
			send_welcome_email,
			to_email=user.email,
			name=validated_data.get("display_name", ""),
			language=language,
		)
		return {"detail": self.CONFIRMATION_DETAIL}


class ChangePasswordSerializer(serializers.Serializer):
	current_password = serializers.CharField(write_only=True)
	new_password = serializers.CharField(write_only=True, validators=[validate_password])

	def validate_current_password(self, value):
		if not self.context["request"].user.check_password(value):
			raise serializers.ValidationError(_("Current password is incorrect."))
		return value


class PasswordResetRequestSerializer(serializers.Serializer):
	"""Sólo valida la forma del email. Que exista o no la cuenta no se
	responde acá ni en ningún lado (RF2)."""

	email = serializers.EmailField()
	language = serializers.CharField(required=False, allow_blank=True)


class PasswordResetConfirmSerializer(serializers.Serializer):
	"""La validación del código y de la contraseña vive en
	accounts.services.password_reset.confirm_reset — un solo lugar, como pide
	el CLAUDE.md. Acá sólo la forma."""

	email = serializers.EmailField()
	code = serializers.CharField(max_length=12)
	new_password = serializers.CharField(write_only=True)
	# Sólo para traducir los errores de validación de la contraseña: la API no
	# tiene LocaleMiddleware, así que sin esto salen siempre en español.
	language = serializers.CharField(required=False, allow_blank=True)


class AccountDeletionSerializer(serializers.Serializer):
	"""Erasure is irreversible, so an access token is not enough on its own —
	the caller re-proves the password. Protects against a device left unlocked
	or a leaked token nuking someone's account."""

	current_password = serializers.CharField(write_only=True)

	def validate_current_password(self, value):
		if not self.context["request"].user.check_password(value):
			raise serializers.ValidationError(_("Current password is incorrect."))
		return value
