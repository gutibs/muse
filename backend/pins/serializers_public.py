"""Serializers for anonymous surfaces.

Every one of these declares its own field list instead of inheriting from
the internal serializers. That is the whole point: `SharedListPublicSerializer`
used to reuse `PinSerializer`, which nests the full `RestaurantSerializer`,
so a stranger holding a share link received `google_place_id`, `phone`,
`approval_status` and the exact coordinates — and any field added upstream
joined them without review.

Shortlists, profile QR codes and shortlist voting each add another anonymous
surface. They all serialize through this module.
"""

from rest_framework import serializers

from accounts.serializers import UserAnonymousSafeSerializer
from pins.models import Pin, SharedList

# A shared list is a link sent to friends, not a catalogue dump. The cap
# bounds how expensive one unauthenticated request can be; `get_pins` used
# to return every pin the owner had.
PUBLIC_PIN_LIMIT = 100


class PublicRestaurantSerializer(serializers.Serializer):
	"""What a shared page needs to render a restaurant, and nothing else.

	Deliberately a plain Serializer rather than a ModelSerializer: a
	ModelSerializer invites `fields = "__all__"` and makes it easy to widen
	the payload by touching the model. Here, adding a public field is an
	explicit decision.
	"""

	id = serializers.IntegerField(read_only=True)
	name = serializers.CharField(read_only=True)
	city = serializers.CharField(read_only=True)
	district = serializers.SerializerMethodField()
	address = serializers.CharField(read_only=True)
	image_url = serializers.CharField(read_only=True)
	price_level = serializers.IntegerField(read_only=True)
	lat = serializers.SerializerMethodField()
	lng = serializers.SerializerMethodField()

	def get_district(self, obj):
		# Column arrives with the tag axes; tolerated as absent until then.
		return getattr(obj, "district", "") or ""

	def get_lat(self, obj):
		return obj.location.y if obj.location else None

	def get_lng(self, obj):
		return obj.location.x if obj.location else None


class PublicTagSerializer(serializers.Serializer):
	"""Tag chips on a shared list. Display only — no id, which is a database
	key the shared page has no use for.

	`kind` sí viaja: sin él la página pública no puede agrupar por eje, y es
	un dato del catálogo, no del dueño de la lista.
	"""

	name = serializers.CharField(read_only=True)
	slug = serializers.CharField(read_only=True)
	kind = serializers.CharField(read_only=True)


class PublicPinSerializer(serializers.Serializer):
	"""A pin as seen by someone who is not logged in.

	No pin `id` and no timestamps: the page shows what the owner
	recommended, not their activity record. The restaurant id doubles as the
	list key, so nothing is lost by withholding the pin's own.
	"""

	restaurant_detail = PublicRestaurantSerializer(source="restaurant", read_only=True)
	tags_detail = PublicTagSerializer(source="tags", many=True, read_only=True)
	status = serializers.CharField(read_only=True)
	rating = serializers.IntegerField(read_only=True)
	comment = serializers.CharField(read_only=True)


class SharedListPublicSerializer(serializers.ModelSerializer):
	# Email-free on purpose: this endpoint answers to anyone holding the link.
	owner = UserAnonymousSafeSerializer(source="user", read_only=True)
	pins = serializers.SerializerMethodField()

	class Meta:
		model = SharedList
		fields = ("id", "title", "owner", "pins", "created_at")

	def get_pins(self, obj):
		qs = Pin.objects.filter(user=obj.user).select_related("restaurant").prefetch_related("tags")
		if obj.status_filter != "all":
			qs = qs.filter(status=obj.status_filter)
		return PublicPinSerializer(qs[:PUBLIC_PIN_LIMIT], many=True).data
