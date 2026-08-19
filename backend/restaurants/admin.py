from django.contrib import admin
from django.contrib.gis import admin as gis_admin

from restaurants.models import Cuisine, MenuItem, Restaurant, Tag


@admin.register(Restaurant)
class RestaurantAdmin(gis_admin.GISModelAdmin):
	list_display = (
		"name",
		"city",
		"country",
		"cuisines_display",
		"approval_status",
		"reservation_status",
		"created_by",
		"created_at",
	)
	search_fields = ("name", "city", "country", "address")
	list_filter = (
		"approval_status",
		# La cola de links de reserva a revisar: filtrar por `pending` con una
		# URL cargada da exactamente lo que falta mirar.
		"reservation_status",
		"reservation_provider",
		"cuisines",
		"price_level",
		"quality_level",
		"tags",
		"city",
	)
	# El proveedor lo deriva el modelo del host de la URL; editarlo a mano sólo
	# serviría para que diga una cosa y la URL apunte a otra.
	readonly_fields = ("created_at", "updated_at", "reservation_provider")
	filter_horizontal = ("cuisines", "tags")

	def cuisines_display(self, obj):
		return ", ".join(c.name for c in obj.cuisines.all())

	cuisines_display.short_description = "Cuisines"
	actions = ["approve_restaurants", "reject_restaurants", "approve_reservation_links"]

	@admin.action(description="Approve selected restaurants")
	def approve_restaurants(self, request, queryset):
		count = queryset.update(approval_status=Restaurant.ApprovalStatus.APPROVED)
		self.message_user(request, f"{count} restaurant(s) approved.")

	@admin.action(description="Reject selected restaurants")
	def reject_restaurants(self, request, queryset):
		count = queryset.update(approval_status=Restaurant.ApprovalStatus.REJECTED)
		self.message_user(request, f"{count} restaurant(s) rejected.")

	@admin.action(description="Approve selected reservation links")
	def approve_reservation_links(self, request, queryset):
		"""Aprobar el link es decir "miré este dominio y es el del
		restaurante". Sólo toca los que tienen URL cargada."""
		count = queryset.exclude(reservation_url="").update(
			reservation_status=Restaurant.ReservationStatus.APPROVED
		)
		self.message_user(request, f"{count} reservation link(s) approved.")


@admin.register(Cuisine)
class CuisineAdmin(admin.ModelAdmin):
	list_display = ("name", "slug")
	prepopulated_fields = {"slug": ("name",)}


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
	list_display = ("name", "slug", "kind")
	list_filter = ("kind",)
	prepopulated_fields = {"slug": ("name",)}


@admin.register(MenuItem)
class MenuItemAdmin(admin.ModelAdmin):
	list_display = ("name", "restaurant", "category", "price", "tags_display")
	list_filter = ("category", "tags")
	search_fields = ("name", "restaurant__name")
	filter_horizontal = ("tags",)

	def tags_display(self, obj):
		return ", ".join(t.name for t in obj.tags.all())

	tags_display.short_description = "Tags"
