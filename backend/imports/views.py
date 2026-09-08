"""La API del importador (F2.G).

El parseo corre **acá, sincrónico**: es rápido y no toca la red, así que la
persona se entera al instante de si su archivo sirve, cuántas filas tiene y
cuáles están rotas. Lo lento —matchear contra Google— queda para el cron.
"""

import logging

from django.utils.translation import gettext_lazy as _
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from imports.models import ImportJob
from imports.serializers import ConfirmSerializer, ImportJobSerializer
from imports.services.parse import ParseError, parse_file
from imports.services.run import confirm_job

logger = logging.getLogger(__name__)

MAX_BYTES = 2 * 1024 * 1024


class ImportJobListView(APIView):
	"""`POST /api/v1/imports/` con el archivo, `GET` para listar los propios."""

	parser_classes = [MultiPartParser, FormParser]

	def get(self, request):
		jobs = ImportJob.objects.filter(user=request.user)[:20]
		return Response(ImportJobSerializer(jobs, many=True).data)

	def post(self, request):
		archivo = request.FILES.get("file")
		if archivo is None:
			return Response({"detail": _("A file is required.")}, status=400)

		if archivo.size > MAX_BYTES:
			return Response({"detail": _("That file is too large (max 2 MB).")}, status=400)

		try:
			filas, errores = parse_file(archivo)
		except ParseError as exc:
			return Response({"detail": str(exc)}, status=400)

		if not filas:
			return Response({"detail": _("No usable rows in that file.")}, status=400)

		job = ImportJob.objects.create(
			user=request.user,
			source=archivo.name[:255],
			# Las filas ilegibles cuentan en el total: si no, la pantalla dice
			# "2 de 4" con tres problemas listados abajo y los números no
			# cierran a la vista de quien subió el archivo.
			total=len(filas) + len(errores),
			# Las filas entran como pendientes; el cron las resuelve. Los
			# errores de parseo viajan desde ya, para que la persona los vea
			# sin esperar el matcheo.
			report=[{**fila, "outcome": "pending"} for fila in filas]
			+ [{**err, "outcome": "unreadable"} for err in errores],
		)
		return Response(ImportJobSerializer(job).data, status=status.HTTP_201_CREATED)


class ImportJobDetailView(APIView):
	"""`GET /api/v1/imports/<id>/` — el estado y el reporte."""

	def get(self, request, pk):
		job = ImportJob.objects.filter(pk=pk, user=request.user).first()
		if job is None:
			return Response({"detail": _("Not found.")}, status=404)
		return Response(ImportJobSerializer(job).data)


class ImportJobConfirmView(APIView):
	"""`POST /api/v1/imports/<id>/confirm/` — crea los pins de lo elegido."""

	def post(self, request, pk):
		job = ImportJob.objects.filter(pk=pk, user=request.user).first()
		if job is None:
			return Response({"detail": _("Not found.")}, status=404)

		serializer = ConfirmSerializer(data=request.data)
		serializer.is_valid(raise_exception=True)

		creados = confirm_job(job, serializer.validated_data["restaurant_ids"])
		return Response({"created": creados, **ImportJobSerializer(job).data})
