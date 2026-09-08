import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { api } from './api.service';
import { castVote, peekVoterKey, removeVote, voterHeaders, voterKeyFor } from './votes.service';

const TOKEN = 'b1f0c0de-0000-4000-8000-000000000000';

/**
 * happy-dom no trae `localStorage` en esta configuración (`setItem` es
 * `undefined`), así que el stub va acá y no en un setup global: cambiar la
 * config de test de todo el repo por un archivo sería desproporcionado.
 */
function stubStorage() {
	const datos = new Map<string, string>();
	Object.defineProperty(globalThis, 'localStorage', {
		configurable: true,
		value: {
			getItem: (k: string) => datos.get(k) ?? null,
			setItem: (k: string, v: string) => datos.set(k, v),
			removeItem: (k: string) => datos.delete(k),
			clear: () => datos.clear(),
		},
	});
}

describe('votes.service', () => {
	beforeEach(stubStorage);
	afterEach(() => vi.restoreAllMocks());

	it('genera una clave de votante y la reusa', () => {
		const primera = voterKeyFor(TOKEN);
		const segunda = voterKeyFor(TOKEN);

		expect(primera).toMatch(/^[0-9a-f-]{36}$/);
		expect(segunda).toBe(primera);
	});

	it('usa una clave distinta por lista', () => {
		// Con una sola clave global, el dueño de dos listas podría
		// correlacionar al mismo votante entre las dos.
		expect(voterKeyFor(TOKEN)).not.toBe(voterKeyFor('otra-lista'));
	});

	it('manda la clave en el header al votar', async () => {
		const spy = vi.spyOn(api, 'postAnon').mockResolvedValue(undefined);

		await castVote(TOKEN, 7);

		expect(spy).toHaveBeenCalledWith(
			`/shared/${TOKEN}/votes/`,
			{ itemId: 7 },
			{ 'X-Muse-Voter': voterKeyFor(TOKEN) }
		);
	});

	it('pega en la URL del item al sacar el voto', async () => {
		const spy = vi.spyOn(api, 'deleteAnon').mockResolvedValue(undefined);

		await removeVote(TOKEN, 7);

		expect(spy).toHaveBeenCalledWith(`/shared/${TOKEN}/votes/7/`, {
			'X-Muse-Voter': voterKeyFor(TOKEN),
		});
	});

	it('mirar la lista no crea una identidad', () => {
		// Cualquiera que abra el link pasaría a tener clave aunque no vote.
		expect(peekVoterKey(TOKEN)).toBeNull();
		expect(voterHeaders(TOKEN)).toEqual({});
	});

	it('una vez que votaste, la carga manda tu clave', () => {
		const clave = voterKeyFor(TOKEN);

		expect(voterHeaders(TOKEN)).toEqual({ 'X-Muse-Voter': clave });
	});
});
