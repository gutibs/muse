import logging

from rest_framework import status
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from analytics.models import Event
from analytics.serializers import EventBatchSerializer

logger = logging.getLogger(__name__)


class EventIngestView(APIView):
	"""`POST /api/v1/analytics/events/` — eventos reportados por el cliente.

	Escritura autenticada y con scope propio: es el único endpoint del
	proyecto cuyo tráfico normal son decenas de filas por sesión, así que
	comparte el throttle `user` con nada.
	"""

	throttle_classes = [ScopedRateThrottle]
	throttle_scope = "analytics"

	def post(self, request):
		serializer = EventBatchSerializer(data=request.data)
		serializer.is_valid(raise_exception=True)
		events = serializer.validated_data["events"]

		Event.objects.bulk_create(
			[
				Event(
					user=request.user,
					name=event["name"],
					restaurant=event.get("restaurant"),
					destination=event.get("destination", ""),
					props=event["props"],
				)
				for event in events
			]
		)

		return Response({"accepted": len(events)}, status=status.HTTP_201_CREATED)
