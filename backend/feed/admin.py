from django.contrib import admin

from feed.models import Activity


@admin.register(Activity)
class ActivityAdmin(admin.ModelAdmin):
	list_display = ("actor", "verb", "pin", "target_user", "created_at")
	list_filter = ("verb",)
	search_fields = ("actor__email", "actor__username")
	readonly_fields = ("created_at",)
