"""Borra Persona, ya vaciada por 0004.

Era el eje de ocasión viviendo en su propio modelo en otra app: la misma
semántica que Tag, sin forma de combinarse con el resto en un filtro. Se
borra ahora, con la tabla vacía en producción, y no cuando haya miles de
pins etiquetados encima.
"""

from django.db import migrations


class Migration(migrations.Migration):
	dependencies = [("pins", "0004_personas_to_tags")]

	operations = [
		migrations.RemoveField(model_name="pin", name="personas"),
		migrations.DeleteModel(name="Persona"),
	]
