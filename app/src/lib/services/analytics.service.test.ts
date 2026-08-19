import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { AuthError } from '$lib/types';

const post = vi.fn();
vi.mock('./api.service', () => ({ api: { post: (...args: unknown[]) => post(...args) } }));

import {
	__resetAnalytics,
	flushAnalytics,
	trackExternalActionClick,
	trackVenueCardView,
} from './analytics.service';

describe('analytics service', () => {
	beforeEach(() => {
		vi.useFakeTimers();
		post.mockReset();
		post.mockResolvedValue({ accepted: 1 });
		sessionStorage.clear();
		__resetAnalytics();
	});

	afterEach(() => {
		vi.useRealTimers();
	});

	it('counts the same card once per session', async () => {
		trackVenueCardView(7, 'feed');
		trackVenueCardView(7, 'feed');
		trackVenueCardView(7, 'search');
		await flushAnalytics();

		expect(post).toHaveBeenCalledTimes(1);
		expect(post.mock.calls[0][1].events).toHaveLength(1);
	});

	it('still remembers a counted card after a page reload', async () => {
		// El registro vivía sólo en memoria del módulo, así que abrir una URL
		// directo en la barra —una carga completa, no una navegación de la
		// SPA— volvía a contar la misma tarjeta. En el APK casi no pasa; en
		// web, cada F5 reabría la cuenta.
		trackVenueCardView(7, 'feed');
		await flushAnalytics();
		post.mockClear();

		__resetAnalytics({ keepStorage: true });

		trackVenueCardView(7, 'feed');
		await flushAnalytics();

		expect(post).not.toHaveBeenCalled();
	});

	it('starts fresh in a new tab', () => {
		trackVenueCardView(7, 'feed');
		sessionStorage.clear();
		__resetAnalytics({ keepStorage: true });
		post.mockClear();

		trackVenueCardView(7, 'feed');

		expect(post).toHaveBeenCalledTimes(0); // encolado, todavía sin flush
		void flushAnalytics();
		expect(post).toHaveBeenCalledTimes(1);
	});

	it('batches views instead of posting one request each', async () => {
		trackVenueCardView(1, 'feed');
		trackVenueCardView(2, 'feed');
		expect(post).not.toHaveBeenCalled();

		await vi.advanceTimersByTimeAsync(5000);

		expect(post).toHaveBeenCalledTimes(1);
		expect(post.mock.calls[0][1].events).toHaveLength(2);
	});

	it('sends an external click immediately', () => {
		// El usuario se está yendo a otra app: esperar la tanda es perder el
		// evento que más importa.
		trackExternalActionClick(9, 'reservation', { provider: 'opentable' });

		expect(post).toHaveBeenCalledTimes(1);
		const [, body] = post.mock.calls[0];
		expect(body.events[0]).toMatchObject({
			name: 'external_action_click',
			restaurant: 9,
			destination: 'reservation',
			props: { provider: 'opentable' },
		});
	});

	it('does not dedupe external clicks', () => {
		trackExternalActionClick(9, 'directions');
		trackExternalActionClick(9, 'directions');

		expect(post).toHaveBeenCalledTimes(2);
	});

	it('stops trying after a 401 instead of retrying every batch', async () => {
		post.mockRejectedValue(new AuthError());

		trackVenueCardView(1, 'feed');
		await flushAnalytics();
		trackVenueCardView(2, 'feed');
		await flushAnalytics();

		expect(post).toHaveBeenCalledTimes(1);
	});

	it('never throws at the caller when the backend fails', async () => {
		post.mockRejectedValue(new Error('boom'));

		trackVenueCardView(1, 'feed');
		await expect(flushAnalytics()).resolves.toBeUndefined();
	});
});
