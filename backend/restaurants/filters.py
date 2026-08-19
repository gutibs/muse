"""Restaurant filtering, in one place and through django-filter.

django-filter was already installed and declared as a global filter backend
(`settings.py`), but it was dead on this viewset: `list` was overridden and
called a hand-rolled `get_queryset_filtered()` without ever going through
`filter_queryset()`, and `nearby` used the bare queryset — so "near me" could
not be combined with any filter at all.

Routing both actions through a FilterSet is what makes the multi-attribute
filter of phase 2 an addition to this class rather than a second filtering
mechanism next to the first.
"""

from django_filters import rest_framework as filters

from restaurants.models import Restaurant


class CommaSeparatedFilter(filters.BaseInFilter, filters.CharFilter):
	"""`?cuisine=italian,japanese` → matches ANY of them.

	OR within one axis is the established behaviour of the cuisine filter and
	the one users expect; AND between different axes is the caller's job.
	"""


class RestaurantFilterSet(filters.FilterSet):
	# `search` rather than `name`: it is the parameter the app already sends,
	# and it stays a name match for now.
	search = filters.CharFilter(field_name="name", lookup_expr="icontains")
	city = filters.CharFilter(field_name="city", lookup_expr="icontains")
	cuisine = CommaSeparatedFilter(field_name="cuisines__slug", distinct=True)

	class Meta:
		model = Restaurant
		fields = ["search", "city", "cuisine"]
