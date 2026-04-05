from django.contrib import admin

from accounts.models import EmailInvitation, Friendship, Profile


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


@admin.register(EmailInvitation)
class EmailInvitationAdmin(admin.ModelAdmin):
	list_display = ("from_user", "email", "accepted", "created_at")
	list_filter = ("accepted",)
	search_fields = ("from_user__email", "email")
	readonly_fields = ("token", "created_at")
