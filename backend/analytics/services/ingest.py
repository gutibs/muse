"""Único punto de escritura de eventos.

Lo usan la view de ingesta, los signals del servidor y los tests. Que sea
uno solo importa por dos motivos: la whitelist de props se aplica siempre
—no sólo cuando el evento entra por HTTP— y el día que haya que agregar
sampling o una cola, hay un solo lugar donde tocarlo.
"""

import logging

from analytics.models import Event

logger = logging.getLogger(__name__)

# Eventos que el cliente puede reportar. `save_to_map` queda deliberadamente
# afuera: es el contador de negocio y lo emite un signal cuando el Pin se
# creó de verdad en la base.
CLIENT_EVENTS = frozenset(
	{
		Event.Name.VENUE_CARD_VIEW,
		Event.Name.VENUE_DETAIL_VIEW,
		Event.Name.EXTERNAL_ACTION_CLICK,
	}
)

# Qué puede viajar dentro de `props`, por evento. Es una whitelist y no una
# blacklist a propósito: con una blacklist, cada clave nueva que invente el
# frontend entra sola, y la política de privacidad declara un contenido
# concreto. `surface` dice desde qué pantalla salió el evento.
ALLOWED_PROPS: dict[str, frozenset[str]] = {
	Event.Name.SAVE_TO_MAP: frozenset({"status"}),
	Event.Name.VENUE_CARD_VIEW: frozenset({"surface"}),
	Event.Name.VENUE_DETAIL_VIEW: frozenset({"surface"}),
	Event.Name.EXTERNAL_ACTION_CLICK: frozenset({"surface", "provider"}),
}

# Los valores son etiquetas cortas, no texto libre del usuario. El tope evita
# que alguien use props como canal para guardar un payload arbitrario.
MAX_PROP_LENGTH = 40


class InvalidPropsError(ValueError):
	"""Props que no pasan la whitelist. La view la traduce a 400."""


def clean_props(name: str, props: dict | None) -> dict:
	"""Devuelve las props válidas para `name` o levanta `InvalidPropsError`.

	Función pura: la llaman el serializer (por donde entra HTTP) y
	`record_event` (por donde entran los signals), para que la regla no
	quede escrita dos veces con dos criterios.
	"""
	if not props:
		return {}
	if not isinstance(props, dict):
		raise InvalidPropsError("props must be an object")

	allowed = ALLOWED_PROPS.get(name, frozenset())
	unknown = set(props) - allowed
	if unknown:
		raise InvalidPropsError(f"unknown props for {name}: {', '.join(sorted(unknown))}")

	cleaned = {}
	for key, value in props.items():
		if not isinstance(value, str):
			raise InvalidPropsError(f"props.{key} must be a string")
		if len(value) > MAX_PROP_LENGTH:
			raise InvalidPropsError(f"props.{key} is too long")
		cleaned[key] = value
	return cleaned


def is_opted_out(user) -> bool:
	"""True si la persona ejerció su derecho de oposición (art. 21 GDPR).

	Se consulta acá, en el único punto de escritura, y no en cada call site:
	un evento que se escapa por una puerta lateral convierte en falsa una
	promesa de la política de privacidad.
	"""
	if user is None or not user.is_authenticated:
		return False
	profile = getattr(user, "profile", None)
	return bool(profile and profile.analytics_opt_out)


def record_event(
	*,
	name: str,
	user=None,
	restaurant=None,
	destination: str = "",
	props: dict | None = None,
) -> Event | None:
	"""Persiste un evento, o devuelve None si la persona se opuso.

	`props` se filtra siempre contra la whitelist.
	"""
	if is_opted_out(user):
		return None

	return Event.objects.create(
		name=name,
		user=user,
		restaurant=restaurant,
		destination=destination,
		props=clean_props(name, props),
	)
