from rest_framework import serializers

from analytics.models import Event
from analytics.services.ingest import CLIENT_EVENTS, InvalidPropsError, clean_props
from restaurants.models import Restaurant

# Tope de eventos por request. El cliente deduplica y manda en tandas; 50
# alcanza de sobra para un scroll largo y evita que un bug del frontend
# mande diez mil filas en un POST.
MAX_BATCH = 50

_NEEDS_RESTAURANT = frozenset(
	{
		Event.Name.VENUE_CARD_VIEW,
		Event.Name.VENUE_DETAIL_VIEW,
		Event.Name.EXTERNAL_ACTION_CLICK,
	}
)


class EventIngestSerializer(serializers.Serializer):
	"""Un evento reportado por el cliente.

	`name` se limita a `CLIENT_EVENTS`: mandar `save_to_map` desde acá es un
	400, no un evento guardado.
	"""

	name = serializers.ChoiceField(choices=sorted(CLIENT_EVENTS))
	restaurant = serializers.PrimaryKeyRelatedField(
		queryset=Restaurant.objects.all(),
		required=False,
		allow_null=True,
	)
	destination = serializers.ChoiceField(
		choices=Event.Destination.choices,
		required=False,
		allow_blank=True,
		default="",
	)
	props = serializers.DictField(required=False, default=dict)

	def validate(self, attrs):
		name = attrs["name"]

		if name in _NEEDS_RESTAURANT and not attrs.get("restaurant"):
			raise serializers.ValidationError({"restaurant": "This event needs a restaurant."})

		if name == Event.Name.EXTERNAL_ACTION_CLICK and not attrs.get("destination"):
			raise serializers.ValidationError({"destination": "This event needs a destination."})

		try:
			attrs["props"] = clean_props(name, attrs.get("props"))
		except InvalidPropsError as exc:
			raise serializers.ValidationError({"props": str(exc)}) from exc

		return attrs


class EventBatchSerializer(serializers.Serializer):
	"""Todo o nada: si un evento del batch está mal, se rechaza el batch
	entero. Aceptar la mitad deja al cliente sin saber qué reintentar, y
	reintentar duplicaría lo que sí entró."""

	events = EventIngestSerializer(many=True, allow_empty=False, max_length=MAX_BATCH)
