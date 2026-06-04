from django.contrib import admin

from accounts.models import ConsentRecord, EmailInvitation, Friendship, Profile


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
