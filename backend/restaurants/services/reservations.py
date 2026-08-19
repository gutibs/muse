"""Clasificación de la URL de reserva.

El campo lo llena quien da de alta el restaurante y el botón se le muestra
después a todos los demás. Es contenido generado por un usuario que apunta
hacia afuera, en la pantalla donde alguien está por dejar su nombre y su
teléfono: si se acepta cualquier dominio, es un canal de phishing con
nuestra marca de fondo.

Tres caminos aprueban solos, y ninguno mira el path — el nombre del
restaurante dentro de la URL no dice nada sobre quién es el dueño del
dominio:

1. El host pertenece a un proveedor conocido.
2. El host coincide con el sitio oficial, que viene del payload de Google.
3. El host lleva el nombre del restaurante.

Lo demás queda `pending`: se guarda, no se muestra, y aparece en la cola del
admin.
"""

import logging
import re
from dataclasses import dataclass
from urllib.parse import urlparse

from django.core.exceptions import ValidationError

from restaurants.models import Restaurant

logger = logging.getLogger(__name__)

# Dominio registrable → proveedor. Se compara contra el host completo o
# contra un sufijo separado por punto, nunca con `in`: `opentable.evil.com`
# contiene "opentable.com" como texto y no tiene nada que ver.
KNOWN_PROVIDERS: dict[str, str] = {
	"opentable.com": Restaurant.ReservationProvider.OPENTABLE,
	"opentable.co.uk": Restaurant.ReservationProvider.OPENTABLE,
	"thefork.com": Restaurant.ReservationProvider.THEFORK,
	"thefork.es": Restaurant.ReservationProvider.THEFORK,
	"thefork.it": Restaurant.ReservationProvider.THEFORK,
	"resy.com": Restaurant.ReservationProvider.RESY,
	"sevenrooms.com": Restaurant.ReservationProvider.SEVENROOMS,
	"quandoo.com": Restaurant.ReservationProvider.QUANDOO,
	"tablecheck.com": Restaurant.ReservationProvider.TABLECHECK,
	"meitre.com": Restaurant.ReservationProvider.MEITRE,
	# Los tres de abajo salieron de mirar qué usan de verdad los venues del
	# catálogo, no de un catálogo de proveedores: Woki es argentino y lo usan
	# dos de los restaurantes con más pins, Tock lo usa Yardbird en Hong Kong,
	# y CoverManager aparece en la región.
	"wokiapp.com": Restaurant.ReservationProvider.WOKI,
	"exploretock.com": Restaurant.ReservationProvider.TOCK,
	"covermanager.com": Restaurant.ReservationProvider.COVERMANAGER,
}

ALLOWED_SCHEMES = frozenset({"http", "https"})

# Un nombre de dominio no distingue acentos ni espacios: para compararlo con
# el nombre del restaurante hay que dejar los dos en el mismo alfabeto.
_NON_ALNUM = re.compile(r"[^a-z0-9]+")
# Con menos de esto, la coincidencia es ruido: "Bar" está dentro de
# cualquier dominio con esas tres letras seguidas.
MIN_NAME_MATCH_LENGTH = 6


@dataclass(frozen=True)
class ReservationClassification:
	provider: str
	status: str


def _host(url: str) -> str:
	parsed = urlparse(url)
	if parsed.scheme.lower() not in ALLOWED_SCHEMES:
		raise ValidationError(f"Unsupported URL scheme: {parsed.scheme or '(none)'}")
	host = (parsed.hostname or "").lower()
	if not host:
		raise ValidationError("The reservation URL has no host.")
	return host.removeprefix("www.")


def _host_or_none(url: str) -> str | None:
	"""Como `_host`, pero para URLs que no controlamos y no queremos validar.

	El sitio oficial se usa sólo como aval: si lo que hay guardado es basura,
	deja de avalar y listo — no es motivo para rechazar la reserva.
	"""
	try:
		return _host(url)
	except ValidationError:
		logger.warning("Restaurant website is not a usable URL: %r", url)
		return None


def _matches_domain(host: str, domain: str) -> bool:
	"""True si `host` es `domain` o un subdominio suyo."""
	return host == domain or host.endswith(f".{domain}")


def _normalise(value: str) -> str:
	return _NON_ALNUM.sub("", value.lower())


def classify_reservation_url(url: str, *, name: str, website: str) -> ReservationClassification:
	"""Devuelve el proveedor y el estado que le corresponden a `url`.

	Levanta `ValidationError` si la URL no es http(s) o no tiene host: eso no
	es una URL pendiente de revisión, es una entrada inválida.
	"""
	host = _host(url)

	for domain, provider in KNOWN_PROVIDERS.items():
		if _matches_domain(host, domain):
			return ReservationClassification(provider, Restaurant.ReservationStatus.APPROVED)

	if website and host == _host_or_none(website):
		return ReservationClassification(
			Restaurant.ReservationProvider.DIRECT,
			Restaurant.ReservationStatus.APPROVED,
		)

	normalised_name = _normalise(name)
	if len(normalised_name) >= MIN_NAME_MATCH_LENGTH and normalised_name in _normalise(host):
		return ReservationClassification(
			Restaurant.ReservationProvider.DIRECT,
			Restaurant.ReservationStatus.APPROVED,
		)

	return ReservationClassification(
		Restaurant.ReservationProvider.OTHER,
		Restaurant.ReservationStatus.PENDING,
	)
