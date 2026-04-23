import L from 'leaflet';

/**
 * Standard Muse circular map pin used across map, user profile, shared list and search routes.
 * White border + soft shadow; size controls the overall diameter.
 */
export function createPinIcon(color: string, size = 28): L.DivIcon {
	return L.divIcon({
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
