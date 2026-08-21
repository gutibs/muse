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
	"""
	owner = owner or viewer
	qs = (
		Pin.objects.filter(user=owner)
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
