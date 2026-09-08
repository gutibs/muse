import { afterEach, describe, expect, it, vi } from 'vitest';
import { readGoogleSuggestions } from './google-suggestions';
import { ApiError } from '$lib/types';
import type { PlaceSuggestion } from '$lib/services/places.service';

const rejected = (reason: unknown): PromiseSettledResult<{ results: PlaceSuggestion[] }> => ({
	status: 'rejected',
	reason,
});

describe('readGoogleSuggestions', () => {
	afterEach(() => vi.restoreAllMocks());

	it('marca un 502 como fallo, no como cero resultados', () => {
		// El bug que arregla: con Google caído la pantalla decía "sin
		// resultados", indistinguible de un restaurante que no existe.
		const state = readGoogleSuggestions(rejected(new ApiError(502, {})), 'search:google');

		expect(state.failed).toBe(true);
		expect(state.results).toEqual([]);
	});

	it('pide el mensaje de "no disponible" cuando Google falló', () => {
		const state = readGoogleSuggestions(rejected(new ApiError(502, {})), 'search:google');

		expect(state.messageKey).toBe('pin.googleUnavailable');
	});

	it('devuelve las sugerencias y no marca fallo cuando Google contestó', () => {
		const place: PlaceSuggestion = { placeId: 'abc', name: 'Trescha', address: 'Berlin' };
		const state = readGoogleSuggestions({ status: 'fulfilled', value: { results: [place] } }, 's');

		expect(state.results).toEqual([place]);
		expect(state.failed).toBe(false);
		expect(state.messageKey).toBeNull();
	});

	it('deja traza del rechazo en la consola, con el scope que le pasan', () => {
		// Sin esto, un reporte de "no me aparece el restaurante" no tiene
		// nada que mirar en devtools: el error se descartaba en silencio.
		const warn = vi.spyOn(console, 'warn').mockImplementation(() => {});

		readGoogleSuggestions(rejected(new ApiError(502, {})), 'search:google');

		expect(warn).toHaveBeenCalledOnce();
		expect(warn.mock.calls[0][0]).toContain('search:google');
	});
});
