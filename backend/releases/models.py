"""La política de versiones que la app consulta al arrancar.

Vive en la base y no en una variable de entorno **a propósito**: el sentido de
todo esto es poder subir el piso sin compilar una app nueva, y con env además
haría falta un deploy. Desde el admin se cambia en segundos, que es lo que hace
falta cuando hay una versión rota dando vueltas.

`store_url` también sale de acá por la misma razón: hoy las tiendas todavía no
están aprobadas y el link es una descarga directa; cuando exista el de la tienda
se cambia sin tocar código.
"""

from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _


def parse_version(raw: str) -> tuple[int, ...]:
	"""`"1.10.0"` → `(1, 10, 0)`, para comparar como versión y no como texto.

	`"1.10.0" < "1.9.0"` es verdadero comparando strings y falso comparando
	versiones. Con el piso mal comparado, una app al día se ve como vieja y la
	persona queda bloqueada sin poder hacer nada.

	Tolera la `V` de `build.gradle`: ahí las versiones se escriben `V1.4.1` y en
	`package.json` `1.4.1`, y las dos formas terminan pasando por acá.
	"""
	limpio = raw.strip().lstrip("Vv")
	partes = []
	for parte in limpio.split("."):
		if not parte.isdigit():
			raise ValueError(f"versión con forma inesperada: {raw!r}")
		partes.append(int(parte))
	if not partes:
		raise ValueError(f"versión vacía: {raw!r}")
	return tuple(partes)


class AppVersion(models.Model):
	"""Qué versión de la app se sigue soportando, por plataforma."""

	class Platform(models.TextChoices):
		ANDROID = "android", "Android"
		IOS = "ios", "iOS"

	platform = models.CharField(max_length=16, choices=Platform.choices, unique=True)
	min_supported = models.CharField(
		max_length=32,
		help_text=_("Below this version the app blocks with no way out. Semantic, e.g. 1.3.0"),
	)
	latest = models.CharField(
		max_length=32,
		help_text=_("Newest published version. Between this and the minimum, the app suggests."),
	)
	store_url = models.URLField(
		blank=True,
		default="",
		help_text=_("Where the blocking screen sends people. Store link, or direct download."),
	)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		verbose_name = _("app version policy")
		verbose_name_plural = _("app version policies")

	def __str__(self) -> str:
		return f"{self.platform}: min {self.min_supported}, latest {self.latest}"

	def clean(self):
		"""Un dedazo acá deja a todo el mundo afuera, así que se valida antes.

		La validación va en el modelo y no en un serializer porque esto se edita
		desde el admin, que es el único camino de escritura: no hay endpoint que
		lo escriba.
		"""
		errores = {}
		for campo in ("min_supported", "latest"):
			try:
				parse_version(getattr(self, campo))
			except ValueError as exc:
				errores[campo] = str(exc)
		if errores:
			raise ValidationError(errores)

		if parse_version(self.min_supported) > parse_version(self.latest):
			raise ValidationError(
				{
					"min_supported": _(
						"The minimum cannot be higher than the latest version: "
						"nobody could ever satisfy it and everyone would be locked out."
					)
				}
			)
