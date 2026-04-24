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

/** Standard Muse pin colors used across map views. */
export const PIN_COLORS = {
	visited: '#5D4E3F',
	toVisit: '#9A8E7E',
	friend: '#C9A678',
} as const;
