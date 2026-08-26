"""Estado de los eventos de analytics en la base local.

    docker compose -f docker-compose.dev.yml exec -T backend \
        python manage.py shell < scripts/ver-eventos.py

Pensado para mirarlo mientras se recorre la app a mano: dice qué se registró,
desde qué pantalla y con qué destino, sin tener que abrir el admin.
"""

from django.db.models import Count
from django.db.models.functions import TruncDate

from analytics.models import Event

total = Event.objects.count()
print(f"eventos: {total}")

for row in Event.objects.values("name").annotate(n=Count("id")).order_by("-n"):
	print(f"  {row['name']:<24} {row['n']}")

print("\núltimos 10:")
for e in Event.objects.select_related("restaurant", "user")[:10]:
	quien = e.user.email if e.user else "(anónimo)"
	donde = e.restaurant.name if e.restaurant else "—"
	extra = f" -> {e.destination}" if e.destination else ""
	print(f"  {e.created_at:%H:%M:%S}  {e.name}{extra}  {donde}  [{quien}]  {e.props}")

# El dedupe es por usuario, venue y **día** (el Set vive en sessionStorage y la
# consolidación mensual cuenta un tap por día). Agrupar sin la fecha marcaba
# como duplicado la misma tarjeta vista el lunes y el miércoles: recorrer la app
# dos días seguidos daba rojo con el dedupe intacto.
repetidos = (
	Event.objects.filter(name=Event.Name.VENUE_CARD_VIEW)
	.annotate(dia=TruncDate("created_at"))
	.values("user_id", "restaurant_id", "dia")
	.annotate(n=Count("id"))
	.filter(n__gt=1)
)
print(f"\ntarjetas contadas más de una vez en el mismo día (debería ser 0): {repetidos.count()}")
for row in repetidos[:5]:
	print(f"  user={row['user_id']} venue={row['restaurant_id']} {row['dia']} → {row['n']}")
