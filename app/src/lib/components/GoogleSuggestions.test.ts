import { cleanup, fireEvent, render } from '@testing-library/svelte';
import { afterEach, describe, expect, it } from 'vitest';
import GoogleSuggestions from './GoogleSuggestions.svelte';
import { i18n } from '$lib/i18n/index.svelte';
import type { PlaceSuggestion } from '$lib/services/places.service';

const PLACES: PlaceSuggestion[] = [
	{ placeId: 'abc', name: 'Trescha', address: 'Berlin' },
	{ placeId: 'def', name: 'i Latina', address: 'Bogotá' },
];

describe('GoogleSuggestions', () => {
	afterEach(cleanup);

	it('avisa cuando no se pudo consultar Google', () => {
		// El bug: con Google caído la pantalla callaba y el usuario leía
		// "sin resultados", como si el restaurante no existiera.
		i18n.setLocale('en');
		const { getByRole } = render(GoogleSuggestions, {
			results: [],
			failed: true,
			messageKey: 'pin.googleUnavailable',
			title: 'From Google',
		});

		expect(getByRole('status').textContent).toContain('temporarily unavailable');
	});

	it('centra el aviso cuando no hay ninguna otra cosa en pantalla', () => {
		// Al fondo de un área vacía, pegado al nav, el aviso no se lee: es
		// tan invisible como el silencio que vino a reemplazar.
		i18n.setLocale('en');
		const { getByRole } = render(GoogleSuggestions, {
			results: [],
			failed: true,
			messageKey: 'pin.googleUnavailable',
			title: 'From Google',
			centered: true,
		});

		expect(getByRole('status').className).toContain('h-full');
	});

	it('lista cada sugerencia como un botón, bajo el título de la sección', () => {
		const { getByRole, getByText } = render(GoogleSuggestions, {
			results: PLACES,
			failed: false,
			messageKey: null,
			title: 'From Google',
		});

		expect(getByText('From Google')).toBeTruthy();
		expect(getByRole('button', { name: /Trescha/ })).toBeTruthy();
		expect(getByRole('button', { name: /i Latina/ })).toBeTruthy();
	});

	it('avisa cuál sugerencia tocó el usuario', async () => {
		const picked: PlaceSuggestion[] = [];
		const { getByRole } = render(GoogleSuggestions, {
			results: PLACES,
			failed: false,
			messageKey: null,
			title: 'From Google',
			onselect: (p: PlaceSuggestion) => picked.push(p),
		});

		await fireEvent.click(getByRole('button', { name: /Trescha/ }));

		expect(picked).toEqual([PLACES[0]]);
	});

	it('bloquea los botones mientras una importación está en curso', () => {
		// Sin esto, dos toques seguidos disparan dos importaciones del mismo
		// lugar y el backend contesta 409 al segundo.
		const { getByRole } = render(GoogleSuggestions, {
			results: PLACES,
			failed: false,
			messageKey: null,
			title: 'From Google',
			importingPlaceId: 'abc',
		});

		expect(getByRole('button', { name: /i Latina/ }).hasAttribute('disabled')).toBe(true);
	});
});
