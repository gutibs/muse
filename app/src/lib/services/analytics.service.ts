import { AuthError } from '$lib/types';
import { logSilent } from '$lib/utils/logger';
import { api } from './api.service';

/**
 * Cola de eventos de producto.
 *
 * Tres reglas que no son de performance sino de que el número signifique algo:
 *
 * - Las vistas se deduplican una vez por sesión y por restaurante. Sin eso, un
 *   scroll que sube y baja por el feed cuenta la misma tarjeta veinte veces y
 *   "cuánta gente vio este venue" pasa a medir el pulgar del usuario.
 * - Los clicks externos se mandan al toque, sin esperar la tanda: el usuario se
 *   está yendo a otra app y puede que no volvamos a tener un momento para
 *   mandarlos.
 * - Nada de esto puede romper la UI. Todo error se logea y se sigue.
 *
 * `save_to_map` no está acá a propósito: lo cuenta el servidor cuando el Pin
 * existe de verdad, y el endpoint rechaza el evento si llega desde el cliente.
 */

type EventName = 'venue_card_view' | 'venue_detail_view' | 'external_action_click';

export type ExternalDestination = 'directions' | 'reservation' | 'website';

/** Pantalla desde la que salió el evento. Etiqueta corta, nunca texto libre. */
export type Surface = 'feed' | 'search' | 'profile' | 'map' | 'restaurant' | 'friend';

interface QueuedEvent {
	name: EventName;
	restaurant: number;
	destination?: ExternalDestination;
	props?: Record<string, string>;
}

/** Espera antes de mandar la tanda. Suficiente para juntar un scroll entero. */
const FLUSH_DELAY_MS = 5000;
/** El backend rechaza batches de más de 50. */
const MAX_BATCH = 20;

/**
 * Dónde se recuerda qué tarjetas ya se contaron.
 *
 * En `sessionStorage` y no sólo en memoria: el registro vivía en el módulo, y
 * abrir una URL directo en la barra —una carga completa, no una navegación de
 * la SPA— lo vaciaba, así que la misma tarjeta se contaba de nuevo. En el APK
 * casi no pasa, porque la app se carga una vez; en web, cada recarga reabría
 * la cuenta. `sessionStorage` sobrevive a la recarga y muere al cerrar la
 * pestaña, que es lo que "una vez por sesión" quiere decir.
 */
const SEEN_KEY = 'muse_analytics_seen';

let queue: QueuedEvent[] = [];
let timer: ReturnType<typeof setTimeout> | null = null;
let disabled = false;
let seen: Set<string> = loadSeen();

function loadSeen(): Set<string> {
	try {
		const raw = sessionStorage.getItem(SEEN_KEY);
		return new Set(raw ? (JSON.parse(raw) as string[]) : []);
	} catch (err) {
		// Storage lleno, deshabilitado o modo privado: se cuenta de más, que
		// es mucho mejor que romper la pantalla por una métrica.
		logSilent('analytics:loadSeen', err);
		return new Set();
	}
}

function persistSeen() {
	try {
		sessionStorage.setItem(SEEN_KEY, JSON.stringify([...seen]));
	} catch (err) {
		logSilent('analytics:persistSeen', err);
	}
}

function scheduleFlush() {
	if (timer !== null) return;
	timer = setTimeout(() => {
		timer = null;
		void flushAnalytics();
	}, FLUSH_DELAY_MS);
}

function enqueue(event: QueuedEvent, immediate = false) {
	if (disabled) return;
	queue.push(event);
	if (immediate || queue.length >= MAX_BATCH) {
		void flushAnalytics();
		return;
	}
	scheduleFlush();
}

/** Manda lo encolado. Se puede llamar a mano al salir de una pantalla. */
export async function flushAnalytics(): Promise<void> {
	if (timer !== null) {
		clearTimeout(timer);
		timer = null;
	}
	if (disabled || queue.length === 0) return;

	const batch = queue;
	queue = [];

	try {
		await api.post('/analytics/events/', { events: batch });
	} catch (err) {
		if (err instanceof AuthError) {
			// Pantalla pública o sesión vencida: no hay a quién atribuirle los
			// eventos. Se apaga para el resto de la sesión en vez de reintentar
			// contra un 401 en cada tanda.
			disabled = true;
		}
		// Los eventos perdidos se pierden: reencolarlos haría crecer la cola sin
		// techo cuando el backend está caído, que es justo cuando menos importa.
		logSilent('analytics:flush', err);
	}
}

function trackViewOnce(name: EventName, restaurantId: number, surface: Surface) {
	const key = `${name}:${restaurantId}`;
	if (seen.has(key)) return;
	seen.add(key);
	persistSeen();
	enqueue({ name, restaurant: restaurantId, props: { surface } });
}

/** La tarjeta entró en pantalla. Una vez por restaurante y por sesión. */
export function trackVenueCardView(restaurantId: number, surface: Surface) {
	trackViewOnce('venue_card_view', restaurantId, surface);
}

/** El usuario abrió la ficha del restaurante. */
export function trackVenueDetailView(restaurantId: number, surface: Surface = 'restaurant') {
	trackViewOnce('venue_detail_view', restaurantId, surface);
}

/**
 * El usuario tocó un botón que lo saca de la app.
 *
 * Sin dedupe del lado del cliente: la tabla guarda el bruto y el reporte
 * agrupa por (usuario, venue, día). Así el mismo número se puede mostrar
 * deduplicado o crudo, y se puede explicar cuál es cuál.
 */
export function trackExternalActionClick(
	restaurantId: number,
	destination: ExternalDestination,
	options: { surface?: Surface; provider?: string } = {}
) {
	const props: Record<string, string> = {};
	if (options.surface) props.surface = options.surface;
	if (options.provider) props.provider = options.provider;
	enqueue({ name: 'external_action_click', restaurant: restaurantId, destination, props }, true);
}

/**
 * Sólo para tests: reinicia el estado del módulo.
 *
 * `keepStorage` simula una recarga de página —el módulo arranca de cero pero
 * `sessionStorage` sigue ahí— que es el caso que hacía contar dos veces.
 */
export function __resetAnalytics({ keepStorage = false } = {}) {
	queue = [];
	disabled = false;
	if (timer !== null) {
		clearTimeout(timer);
		timer = null;
	}
	if (keepStorage) {
		seen = loadSeen();
		return;
	}
	seen = new Set();
	persistSeen();
}
