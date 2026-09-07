"""El endpoint que consulta la app al arrancar.

Anónimo por necesidad: corre antes de cualquier login, y una app bloqueada por
una versión vieja puede ni siquiera poder autenticarse.
"""

from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from releases.models import AppVersion

# Lo que se contesta cuando no hay política para esa plataforma. **No es un
# error**: iOS todavía no tiene fila, y devolver 404 obligaría a la app a
# interpretar un error — cualquier interpretación que bloquee deja a la gente
# afuera por una fila que falta en una tabla.
SIN_POLITICA = {"minSupported": "0.0.0", "latest": "0.0.0", "storeUrl": ""}


class AppVersionView(APIView):
	"""`GET /api/v1/app-version/?platform=android`"""

	permission_classes = [AllowAny]
	throttle_classes = [ScopedRateThrottle]
	throttle_scope = "app_version"

	def get(self, request):
		platform = request.query_params.get("platform", "")
		policy = AppVersion.objects.filter(platform=platform).first()
		if policy is None:
			return Response(SIN_POLITICA)
		return Response(
			{
				"minSupported": policy.min_supported,
				"latest": policy.latest,
				"storeUrl": policy.store_url,
			}
		)
