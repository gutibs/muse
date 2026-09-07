from rest_framework import serializers

from imports.models import ImportJob


class ImportJobSerializer(serializers.ModelSerializer):
	class Meta:
		model = ImportJob
		fields = [
			"id",
			"source",
			"state",
			"total",
			"processed",
			"matched",
			"failed",
			"report",
			"created_at",
		]
		read_only_fields = fields


class ConfirmSerializer(serializers.Serializer):
	"""Los ids que la persona eligió de su propio reporte.

	No se validan contra el catálogo acá: `confirm_job` los cruza contra el
	reporte del job, que es la única fuente que importa — un id que nunca salió
	de su archivo no se pinea aunque exista.
	"""

	restaurant_ids = serializers.ListField(child=serializers.IntegerField(), allow_empty=True)
