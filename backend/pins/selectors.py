"""The single way to build a queryset of Pins.

Four call sites used to assemble this by hand — `PinViewSet.get_queryset`,
`UserPinsView.get_queryset`, the shared-list serializer and the feed — each
with its own copy of the `select_related`/`prefetch_related` pair and, worse,
its own reading of `?status=`. `PinViewSet` treated `status=all` as "no
filter" while `UserPinsView` passed it straight to `.filter(status="all")`,
so the same query string returned a friend's whole list on one endpoint and
nothing at all on the other.

Filters that arrive later — favourites, collections, tag axes, visibility
levels — belong here, so that every surface inherits them instead of only
the one that happened to be edited.
"""

from accounts.services.visibility import visible_pin_filter
from pins.models import Pin

# Sentinel the frontend sends to mean "don't filter". Accepted explicitly so
# clients can always pass a status parameter instead of conditionally
# omitting it.
STATUS_ALL = "all"


def visible_pins(viewer, *, owner=None, status=None, tag=None, city=None, favourite=None):
	"""Pins owned by `owner` that `viewer` is allowed to see.

	`owner` defaults to `viewer`, i.e. your own pins. Permission is the
	caller's job — use `accounts.services.visibility.require_can_view` before
	calling this for someone else's pins, so the caller controls whether an
	unauthorised viewer gets a 403 or an empty list.

	El nivel de cada pin se aplica acá y no en las views: `require_can_view`
	decide si el viewer puede mirar a esta persona, `visible_pin_filter`
	decide cuáles de sus pins. Sobre los propios no cambia nada — el dueño
	siempre se ve todo lo suyo.
	"""
	owner = owner or viewer
	qs = (
		Pin.objects.filter(user=owner)
		.filter(visible_pin_filter(viewer))
		.select_related("restaurant")
		.prefetch_related("tags", "restaurant__cuisines")
	)

	if status and status != STATUS_ALL:
		qs = qs.filter(status=status)
	if tag:
		qs = qs.filter(tags__slug=tag)
	if favourite:
		qs = qs.filter(is_favourite=True)
	if city:
		qs = qs.filter(restaurant__city__icontains=city)
	return qs


def reachable_shared_lists():
	"""Las listas que un link puede abrir: activas y no vencidas.

	Vive acá porque son dos vistas las que necesitan exactamente este
	criterio —la página pública y la votación— y una copia por vista es el
	camino conocido a que una acepte lo que la otra rechaza. Una lista
	vencida es un 404 igual que una desactivada: quien tiene el link no
	tiene por qué saber si existió.
	"""
	from django.db.models import Q
	from django.utils import timezone

	from pins.models import SharedList

	return SharedList.objects.filter(is_active=True).filter(
		Q(expires_at__isnull=True) | Q(expires_at__gt=timezone.now())
	)


def votable_shared_lists():
	"""Las listas sobre las que se puede votar.

	Además de ser alcanzable, la lista tiene que ser curada y tener el
	interruptor prendido por su dueño. Sin el `kind`, un link `auto` con
	items colgados a mano aceptaría votos que su dueño nunca ofreció.
	"""
	from pins.models import SharedList

	return reachable_shared_lists().filter(
		kind=SharedList.Kind.CURATED,
		voting_enabled=True,
	)
