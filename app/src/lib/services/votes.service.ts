import { api } from '$lib/services/api.service';

/**
 * La identidad del votante en una shortlist pública.
 *
 * Es un UUID que genera el navegador y guarda en `localStorage`. **Evita el
 * doble voto accidental y nada más**: quien quiera inflar el conteo abre una
 * pestaña de incógnito. Lo único que hay del otro lado es el throttle por IP,
 * y la pantalla no promete otra cosa.
 *
 * Una clave por lista, no una global: con una sola, el dueño de dos listas
 * podría correlacionar al mismo votante entre las dos.
 */
const VOTER_HEADER = 'X-Muse-Voter';

function storageKey(token: string): string {
	return `muse:voter:${token}`;
}

export function voterKeyFor(token: string): string {
	const guardada = localStorage.getItem(storageKey(token));
	if (guardada) return guardada;

	const nueva = crypto.randomUUID();
	localStorage.setItem(storageKey(token), nueva);
	return nueva;
}

/**
 * La clave si ya existe, sin crear una.
 *
 * La carga de la lista la usa para que el servidor diga qué votó quien mira:
 * `voterKeyFor` inventaría una identidad para cualquiera que abre el link sin
 * haber votado nunca.
 */
export function peekVoterKey(token: string): string | null {
	return localStorage.getItem(storageKey(token));
}

export function voterHeaders(token: string): Record<string, string> {
	const clave = peekVoterKey(token);
	return clave ? { [VOTER_HEADER]: clave } : {};
}

function headers(token: string): Record<string, string> {
	return { [VOTER_HEADER]: voterKeyFor(token) };
}

export function castVote(token: string, itemId: number): Promise<void> {
	return api.postAnon(`/shared/${token}/votes/`, { itemId }, headers(token));
}

export function removeVote(token: string, itemId: number): Promise<void> {
	return api.deleteAnon(`/shared/${token}/votes/${itemId}/`, headers(token));
}
