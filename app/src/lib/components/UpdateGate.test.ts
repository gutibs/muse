import { fireEvent, render } from '@testing-library/svelte';
import { describe, expect, it } from 'vitest';
import UpdateGate from './UpdateGate.svelte';
import type { VersionCheck } from '$lib/services/version.service';

const check = (over: Partial<VersionCheck> = {}): VersionCheck => ({
	state: 'ok',
	storeUrl: 'https://x.test/apk',
	latest: '1.4.1',
	...over
});

describe('UpdateGate', () => {
	it('al día no dibuja nada', () => {
		const { queryByTestId } = render(UpdateGate, { props: { check: check() } });
		expect(queryByTestId('update-required')).toBeNull();
		expect(queryByTestId('update-available')).toBeNull();
	});

	it('por debajo del mínimo, pantalla sin salida', () => {
		const { getByTestId, container } = render(UpdateGate, {
			props: { check: check({ state: 'blocked' }) }
		});
		expect(getByTestId('update-required')).toBeTruthy();
		// Sin salida es literal: no hay botón de cerrar ni de descartar. El
		// único control es el link de actualizar.
		expect(container.querySelector('button')).toBeNull();
	});

	it('bloquea sin link, explicando qué hacer en vez de quedar muda', () => {
		// `store_url` arranca vacío: las tiendas no están aprobadas todavía.
		// Las consultas van contra `container` y no contra el documento: sin
		// cleanup automático, un `queryByRole` global encuentra lo que dejó el
		// test anterior.
		const { getByTestId, container } = render(UpdateGate, {
			props: { check: check({ state: 'blocked', storeUrl: '' }) }
		});
		expect(getByTestId('update-no-link')).toBeTruthy();
		expect(container.querySelector('a')).toBeNull();
	});

	it('desactualizada sugiere, y se puede descartar', async () => {
		const { getByTestId, queryByTestId, getByLabelText } = render(UpdateGate, {
			props: { check: check({ state: 'outdated' }) }
		});
		expect(getByTestId('update-available')).toBeTruthy();

		await fireEvent.click(getByLabelText('Dismiss'));
		expect(queryByTestId('update-available')).toBeNull();
	});

	it('la sugerencia no tapa la app', () => {
		const { container } = render(UpdateGate, { props: { check: check({ state: 'outdated' }) } });
		const banner = container.querySelector('[data-testid="update-available"]');
		expect(banner?.className).not.toContain('inset-0');
	});

	it('la bloqueante sí tapa todo', () => {
		const { container } = render(UpdateGate, { props: { check: check({ state: 'blocked' }) } });
		const pantalla = container.querySelector('[data-testid="update-required"]');
		expect(pantalla?.className).toContain('inset-0');
	});
});
