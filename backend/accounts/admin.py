import logging

from django.contrib import admin

from accounts.models import Block, ConsentRecord, EmailInvitation, Friendship, Profile, Report

logger = logging.getLogger(__name__)


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
	"""El panel desde el que se otorga y se quita el Verified Insider.

	Es el único camino: el campo es de sólo lectura por la API. Hay dos formas
	porque resuelven cosas distintas — el tilde en el listado para una persona
	suelta, las acciones en masa para varias de una.
	"""

	list_display = ("user", "display_name", "city", "is_verified_insider", "created_at")
	search_fields = ("user__email", "user__username", "display_name", "city")
	list_filter = ("is_verified_insider", "city")
	list_editable = ("is_verified_insider",)
	readonly_fields = ("created_at", "updated_at")
	actions = ("grant_insider", "revoke_insider")

	@admin.action(description="Marcar como Verified Insider")
	def grant_insider(self, request, queryset):
		self._set_insider(request, queryset, True)

	@admin.action(description="Quitar Verified Insider")
	def revoke_insider(self, request, queryset):
		self._set_insider(request, queryset, False)

	def _set_insider(self, request, queryset, value):
		"""El `.update()` no pasa por el form, así que tampoco por LogEntry.

		Django escribe la entrada de auditoría desde `ModelAdmin.save_model`,
		que una acción en masa no llama. Sin este log, otorgar el badge a
		veinte personas de una no deja rastro de quién lo hizo: queda el
		booleano y nada más.
		"""
		affected = list(queryset.values_list("user__username", flat=True))
		updated = queryset.update(is_verified_insider=value)
		logger.info(
			"Verified Insider %s by %s for %d profile(s): %s",
			"granted" if value else "revoked",
			getattr(request.user, "username", "?"),
			updated,
			", ".join(affected),
		)
		self.message_user(
			request,
			f"{updated} perfil(es) {'marcados como' if value else 'sin'} Verified Insider.",
		)


@admin.register(Friendship)
class FriendshipAdmin(admin.ModelAdmin):
	list_display = ("from_user", "to_user", "status", "created_at")
	list_filter = ("status",)
	search_fields = (
		"from_user__email",
		"from_user__username",
		"to_user__email",
		"to_user__username",
	)
	readonly_fields = ("created_at", "updated_at")


@admin.register(ConsentRecord)
class ConsentRecordAdmin(admin.ModelAdmin):
	"""Audit log of data-protection consent. Read-only: these rows are legal
	evidence and must never be edited or hand-created from the admin."""

	list_display = ("user", "policy", "policy_version", "accepted_at", "ip_address")
	list_filter = ("policy", "policy_version")
	search_fields = ("user__email", "user__username", "ip_address")
	readonly_fields = ("user", "policy", "policy_version", "accepted_at", "ip_address")

	def has_add_permission(self, request):
		return False

	def has_change_permission(self, request, obj=None):
		return False

	def has_delete_permission(self, request, obj=None):
		return False


@admin.register(EmailInvitation)
class EmailInvitationAdmin(admin.ModelAdmin):
	list_display = ("from_user", "email", "accepted", "created_at")
	list_filter = ("accepted",)
	search_fields = ("from_user__email", "email")
	readonly_fields = ("token", "created_at")


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
	"""La cola de moderación. No hay pantalla propia en la app: para el volumen
	del beta esto alcanza, y es lo que hace que el endpoint de reportes cumpla
	la Guideline 1.2 —que pide poder actuar, no sólo recibir—.

	El orden lo da el modelo: pendientes primero y, dentro de cada grupo, lo
	más viejo arriba.
	"""

	list_display = (
		"id",
		"reason",
		"status",
		"reported_user",
		"pin",
		"reported_comment",
		"created_at",
		"resolved_at",
	)
	list_filter = ("status", "reason", "created_at")
	search_fields = (
		"reporter__email",
		"reported_user__email",
		"detail",
		"reported_comment",
	)
	# La denuncia no se edita: se resuelve. Lo único que toca el moderador es
	# el status y la nota; el resto es el registro de lo que pasó.
	readonly_fields = (
		"reporter",
		"reported_user",
		"pin",
		"reason",
		"detail",
		"reported_comment",
		"reported_rating",
		"created_at",
		"resolved_at",
	)

	def has_delete_permission(self, request, obj=None):
		# Una denuncia se cierra con el status, no borrándola: la fila es la
		# constancia de que se actuó, que es lo que pide la Guideline 1.2.
		return False


@admin.register(Block)
class BlockAdmin(admin.ModelAdmin):
	"""Sólo lectura: sirve para entender un reporte —si las dos personas ya se
	bloquearon, el conflicto puede estar resuelto solo— no para intervenir. Un
	bloqueo lo pone y lo saca su dueño."""

	list_display = ("blocker", "blocked", "created_at")
	search_fields = ("blocker__email", "blocked__email")
	readonly_fields = ("blocker", "blocked", "created_at")

	def has_add_permission(self, request):
		return False

	def has_change_permission(self, request, obj=None):
		return False

	def has_delete_permission(self, request, obj=None):
		# Borrarlo desde acá sería desbloquear en nombre de la víctima, sin
		# dejar rastro: `unblock_user` ni se entera, así que no hay log.
		return False
