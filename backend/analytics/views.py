import logging

from rest_framework import status
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from analytics.models import Event
from analytics.serializers import EventBatchSerializer
from analytics.services.ingest import is_opted_out

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

		if is_opted_out(request.user):
			# Se acepta y se descarta. Devolver un error obligaría a la app a
			# manejar un caso que no es un fallo, y el cliente no tiene por
			# qué enterarse de una decisión de privacidad del servidor.
			return Response({"accepted": 0}, status=status.HTTP_201_CREATED)

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
