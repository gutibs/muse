/**
 * Salidas hacia afuera de la app.
 *
 * Único lugar que abre una URL externa. Importa que sea uno solo: dentro del
 * WebView de Capacitor, "abrir un link" no es lo mismo que en un navegador, y
 * si mañana hace falta `@capacitor/browser` se cambia acá y no en cada botón.
 *
 * `noopener` no es decorativo: sin él la página que abrimos recibe una
 * referencia a la nuestra por `window.opener`.
 */
export function openExternal(url: string): void {
	window.open(url, '_blank', 'noopener');
}

/**
 * Link a las indicaciones hasta un punto.
 *
 * Se usa la URL universal de Google Maps y no un esquema propio
 * (`maps://`, `comgooglemaps://`) a propósito: los esquemas custom exigen
 * declarar `LSApplicationQueriesSchemes` en iOS y fallan en silencio si la
 * app no está instalada. Esta URL abre la app de Maps cuando está, y el
 * navegador cuando no.
 */
export function directionsUrl(lat: number, lng: number): string {
	return `https://www.google.com/maps/dir/?api=1&destination=${lat},${lng}`;
}
