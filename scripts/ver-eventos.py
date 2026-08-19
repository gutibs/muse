"""Estado de los eventos de analytics en la base local.

    docker compose -f docker-compose.dev.yml exec -T backend \
        python manage.py shell < scripts/ver-eventos.py

Pensado para mirarlo mientras se recorre la app a mano: dice qué se registró,
desde qué pantalla y con qué destino, sin tener que abrir el admin.
"""

from django.db.models import Count

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

repetidos = (
	Event.objects.filter(name=Event.Name.VENUE_CARD_VIEW)
	.values("user_id", "restaurant_id")
	.annotate(n=Count("id"))
	.filter(n__gt=1)
)
print(f"\ntarjetas contadas más de una vez (debería ser 0): {repetidos.count()}")
