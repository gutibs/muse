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
	insider = filters.BooleanFilter(method="filter_insider", label="Pinned by a Verified Insider")

	class Meta:
		model = Restaurant
		fields = ["search", "city", "cuisine", "insider"]

	def filter_insider(self, queryset, name, value):
		"""Restaurantes donde pineó alguien verificado — y que vos podés ver.

		El `visible_pin_filter` no es opcional ni una precaución de más: sin
		él la pregunta "¿dónde pinean los Insiders?" se contesta con pins
		privados, y el restaurante aparece en el listado *porque* alguien lo
		guardó en secreto. El filtro sería entonces un oráculo sobre datos que
		su dueño marcó como suyos, que es justo lo que F2.A vino a cerrar.

		Import diferido como en `restaurants/serializers.py`: `pins` importa
		este paquete.
		"""
		if not value:
			return queryset

		from accounts.services.visibility import visible_pin_filter
		from pins.models import Pin

		visible_insider_pins = Pin.objects.filter(
			visible_pin_filter(self.request.user if self.request else None)
		).filter(user__profile__is_verified_insider=True)
		return queryset.filter(pk__in=visible_insider_pins.values("restaurant_id"))
