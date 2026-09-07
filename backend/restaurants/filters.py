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

from restaurants.models import Restaurant, Tag


class CommaSeparatedFilter(filters.BaseInFilter, filters.CharFilter):
	"""`?cuisine=italian,japanese` → matches ANY of them.

	OR within one axis is the established behaviour of the cuisine filter and
	the one users expect; AND between different axes is the caller's job.
	"""


class TagAxisFilter(CommaSeparatedFilter):
	"""Un eje de la taxonomía: OR adentro, y AND contra los demás ejes.

	**El AND necesita un join propio por eje, y ese es todo el punto de esta
	clase.** Los tres ejes viven en la misma M2M distinguidos por `Tag.kind`,
	así que lo intuitivo —juntar todos los slugs en un solo
	`tags__slug__in=[...]`— compila, corre, no falla y devuelve **de más**: se
	convierte en un OR silencioso. Un filtro que miente así no se nota mirando
	la pantalla, porque los resultados de sobra se parecen a los correctos.

	Cada llamada a `.filter(tags__slug__in=...)` sobre un M2M agrega un join
	nuevo, así que encadenarlas —una por eje— es lo que produce el AND real.
	`test_dos_ejes_distintos_se_cruzan` fija exactamente eso.
	"""

	def __init__(self, *args, kind: str, **kwargs):
		self.kind = kind
		kwargs.setdefault("distinct", True)
		super().__init__(*args, **kwargs)

	def filter(self, qs, value):
		if not value:
			return qs
		# `kind` acota el eje: sin esto, un slug de vibe pasado como occasion
		# filtraría igual, y los ejes dejarían de significar algo.
		return qs.filter(tags__slug__in=value, tags__kind=self.kind).distinct()


class RestaurantFilterSet(filters.FilterSet):
	# `search` rather than `name`: it is the parameter the app already sends,
	# and it stays a name match for now.
	search = filters.CharFilter(field_name="name", lookup_expr="icontains")
	city = filters.CharFilter(field_name="city", lookup_expr="icontains")
	cuisine = CommaSeparatedFilter(field_name="cuisines__slug", distinct=True)
	insider = filters.BooleanFilter(method="filter_insider", label="Pinned by a Verified Insider")

	# Los cuatro ejes de la taxonomía (F2.C). Se declaran uno por uno y no en un
	# loop para que el schema del filtro se lea de un vistazo.
	vibe = TagAxisFilter(kind=Tag.Kind.VIBE)
	occasion = TagAxisFilter(kind=Tag.Kind.OCCASION)
	scene = TagAxisFilter(kind=Tag.Kind.SCENE)
	dietary = TagAxisFilter(kind=Tag.Kind.DIETARY)

	class Meta:
		model = Restaurant
		fields = ["search", "city", "cuisine", "insider", "vibe", "occasion", "scene", "dietary"]

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
