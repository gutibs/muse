const ENTITIES: Record<string, string> = {
	'&': '&amp;',
	'<': '&lt;',
	'>': '&gt;',
	'"': '&quot;',
	"'": '&#39;',
};

/**
 * Escape HTML-special characters for safe interpolation into the inline
 * popup HTML used by Leaflet markers. Restaurant names, cities, etc. come
 * from user input and Google Places — never trust them as HTML.
 */
export function escapeHtml(s: string): string {
	return s.replace(/[&<>"']/g, (c) => ENTITIES[c]!);
}
