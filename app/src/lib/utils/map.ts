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
