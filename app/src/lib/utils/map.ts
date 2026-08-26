import type L from 'leaflet';

/**
 * Standard Muse circular map pin used across map, user profile, shared list and search routes.
 * Takes the Leaflet namespace as a parameter so this module stays SSR-safe: importing
 * 'leaflet' at the top-level triggers `window is not defined` during SvelteKit prerender.
 */
export function createPinIcon(Leaflet: typeof L, color: string, size = 28): L.DivIcon {
	return Leaflet.divIcon({
		className: '',
		html: `<div style="width:${size}px;height:${size}px;background:${color};border:3px solid white;border-radius:50%;box-shadow:0 2px 6px rgba(0,0,0,0.2);"></div>`,
		iconSize: [size, size],
		iconAnchor: [size / 2, size / 2],
	});
}

/** Standard Muse pin colors used across map views.
 * Picked for high contrast on small Android screens — taupe palette was
 * indistinguishable on amoled displays per Jess feedback (Apr 2026). */
export const PIN_COLORS = {
	visited: '#16A34A',  // green — rated
	toVisit: '#F97316',  // orange — on the list
	friend: '#6366F1',   // indigo — distinct from rated/unrated
} as const;

/**
 * Tile provider. Was pasted into three components; changing it meant three
 * edits and it was a matter of time before one got missed.
 *
 * CARTO pasó a exigir key y, en vez de responder un error, sirve el mismo PNG
 * con "API KEY REQUIRED" estampado encima — así que el mapa "anda" y se ve
 * roto. Dos detalles que cuestan una tarde si se erran: el parámetro es `key`
 * (con `api_key` devuelve el tile marcado, mismo byte por byte que sin key), y
 * la ruta lleva el prefijo `rastertiles/` (la vieja `light_all/` suelta ignora
 * la key). Verificado tile por tile contra la CDN.
 */
const CARTO_KEY = import.meta.env.VITE_CARTO_KEY;
/** Exportada sólo para que `map.test.ts` pueda fijar la ruta y el parámetro. */
export const TILE_URL =
	'https://{s}.basemaps.cartocdn.com/rastertiles/light_all/{z}/{x}/{y}{r}.png' +
	(CARTO_KEY ? `?key=${CARTO_KEY}` : '');
const ATTRIBUTION =
	'&copy; <a href="https://carto.com/">CARTO</a> &copy; <a href="https://www.openstreetmap.org/copyright">OSM</a>';

// Sin key el mapa sigue funcionando, pero con la marca de agua encima. Es el
// tipo de fallo que nadie reporta como bug porque "el mapa se ve": conviene
// que grite en la consola de quien desarrolla.
if (import.meta.env.DEV && !CARTO_KEY) {
	console.warn(
		'[muse] Falta VITE_CARTO_KEY: los tiles del mapa van a venir con la marca de agua "API KEY REQUIRED".\n' +
			'Copiá la key en app/.env — se pide gratis en https://carto.com/basemaps/apikey/'
	);
}

/**
 * Load the Leaflet namespace and its stylesheet.
 *
 * Dynamic because a top-level `import 'leaflet'` blows up during SvelteKit
 * prerender with `window is not defined`.
 */
export async function loadLeaflet(): Promise<typeof L> {
	const [leaflet] = await Promise.all([import('leaflet'), import('leaflet/dist/leaflet.css')]);
	return leaflet.default;
}

export interface CreateMapOptions {
	center?: [number, number];
	zoom?: number;
	/** Bottom-right zoom buttons. Off for the small picker map. */
	zoomControl?: boolean;
}

/**
 * Create a map with the Muse defaults.
 *
 * Three components used to bootstrap Leaflet themselves with the tile URL
 * copied into each. PinsMap and MapView were near-identical; LocationPicker
 * had genuinely drifted — no minZoom, no maxBounds, no noWrap and no
 * attribution control, so it allowed infinite zoom-out, repeated the world
 * horizontally, and displayed no CARTO/OSM credit at all, which their terms
 * require.
 */
export function createMap(
	Leaflet: typeof L,
	container: HTMLElement,
	{ center = [0, 0], zoom = 2, zoomControl = true }: CreateMapOptions = {}
): L.Map {
	const map = Leaflet.map(container, {
		// Both off in the constructor: the controls are added below at the
		// position we want rather than at Leaflet's defaults.
		zoomControl: false,
		attributionControl: false,
		minZoom: 3,
		maxBoundsViscosity: 1.0,
		maxBounds: [
			[-85, -180],
			[85, 180],
		],
	}).setView(center, zoom);

	Leaflet.tileLayer(TILE_URL, { maxZoom: 19, noWrap: true }).addTo(map);

	Leaflet.control
		.attribution({ position: 'bottomright', prefix: false })
		.addAttribution(ATTRIBUTION)
		.addTo(map);

	if (zoomControl) {
		Leaflet.control.zoom({ position: 'bottomright' }).addTo(map);
	}

	return map;
}
