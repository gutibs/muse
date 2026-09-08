"""Vistas anónimas de shortlists.

Separadas de `pins/views.py` por la misma razón que `serializers_public.py`:
acá no hay `request.user` contra el cual filtrar, así que cada control de
acceso es explícito y se lee de un vistazo. Mezcladas con las vistas
autenticadas, una de estas parece una más y nadie la mira dos veces.
"""

from django.shortcuts import get_object_or_404
from django.utils.translation import gettext_lazy as _
from rest_framework import permissions, status, views
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle

from pins.models import SharedListItem, ShortlistVote
from pins.selectors import votable_shared_lists
from pins.serializers_public import voter_key_from


def _clave_o_400(request):
	"""Votar exige una clave válida; mirar no.

	Un cliente sin clave no puede votar de forma idempotente —cada request
	sería un voto nuevo— así que el 400 es lo correcto, no un voto anónimo
	imposible de sacar después.
	"""
	clave = voter_key_from(request)
	if clave is None:
		raise ValidationError({"voter_key": _("A valid voter key is required.")})
	return clave


def _item_votable(token, item_id):
	"""El item de una lista votable, o 404.

	Las dos operaciones resuelven exactamente lo mismo, y que un item
	pertenezca a la lista del token es lo que vuelve inútil probar ids
	ajenos: uno de otra lista no existe dentro de este token.
	"""
	lista = get_object_or_404(votable_shared_lists(), token=token)
	return get_object_or_404(SharedListItem, pk=item_id, shared_list=lista)


class ShortlistVoteView(views.APIView):
	"""Poner un voto. Idempotente: repetirlo no duplica el conteo."""

	permission_classes = (permissions.AllowAny,)
	authentication_classes = ()
	throttle_classes = (ScopedRateThrottle,)
	throttle_scope = "shortlist_vote"

	def post(self, request, token):
		clave = _clave_o_400(request)
		item = _item_votable(token, request.data.get("item_id"))
		_, creado = ShortlistVote.objects.get_or_create(item=item, voter_key=clave)
		return Response(status=status.HTTP_201_CREATED if creado else status.HTTP_200_OK)


class ShortlistVoteDetailView(views.APIView):
	"""Sacar un voto. 204 aunque no existiera, por la misma razón."""

	permission_classes = (permissions.AllowAny,)
	authentication_classes = ()
	throttle_classes = (ScopedRateThrottle,)
	throttle_scope = "shortlist_vote"

	def delete(self, request, token, item_id):
		clave = _clave_o_400(request)
		item = _item_votable(token, item_id)
		ShortlistVote.objects.filter(item=item, voter_key=clave).delete()
		return Response(status=status.HTTP_204_NO_CONTENT)
