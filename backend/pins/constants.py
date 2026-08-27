"""Valores compartidos por el modelo de pins y por quien decide quién los ve.

`Visibility` vive acá y no dentro de `Pin` porque `Profile` también lo
necesita para su preferencia por defecto, y un modelo importando el módulo
de modelos de otra app para leer un enum ata el orden de carga de las apps
sin ninguna necesidad.
"""

from django.db import models


class Visibility(models.TextChoices):
	PUBLIC = "public", "Public"
	FRIENDS = "friends", "Friends only"
	PRIVATE = "private", "Private"
