from django.contrib import admin

from accounts.models import Block, ConsentRecord, EmailInvitation, Friendship, Profile, Report


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
	list_display = ("user", "display_name", "city", "created_at")
	search_fields = ("user__email", "user__username", "display_name", "city")
	list_filter = ("city",)
	readonly_fields = ("created_at", "updated_at")


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
