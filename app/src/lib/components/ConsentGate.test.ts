import { fireEvent, render, waitFor } from '@testing-library/svelte';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import ConsentGate from './ConsentGate.svelte';
import { authStore } from '$lib/stores/auth.store.svelte';

vi.mock('$lib/stores/auth.store.svelte', () => ({
	authStore: { acceptPolicies: vi.fn() }
}));

/**
 * Frena a las cuentas sin ninguna constancia de consentimiento: en producción,
 * 16 de 17. Lo que importa es que no haya forma de salir sin aceptar y que un
 * fallo no lo deje pasar igual.
 */
describe('ConsentGate', () => {
	beforeEach(() => {
		vi.mocked(authStore.acceptPolicies).mockReset().mockResolvedValue(undefined as never);
	});

	it('muestra los dos documentos que se están aceptando', () => {
		const { container } = render(ConsentGate);
		const hrefs = [...container.querySelectorAll('a')].map((a) => a.getAttribute('href') ?? '');

		expect(hrefs.some((h) => h.includes('privacy'))).toBe(true);
		expect(hrefs.some((h) => h.includes('terms'))).toBe(true);
	});

	it('aceptar deja constancia', async () => {
		const { container } = render(ConsentGate);

		await fireEvent.click(container.querySelector('[data-testid="consent-gate-accept"]'));

		await waitFor(() => expect(authStore.acceptPolicies).toHaveBeenCalledOnce());
	});

	it('si falla no deja pasar: el gate sigue en pantalla', async () => {
		vi.mocked(authStore.acceptPolicies).mockRejectedValue(new Error('sin red'));
		const { container } = render(ConsentGate);

		await fireEvent.click(container.querySelector('[data-testid="consent-gate-accept"]'));

		await waitFor(() => expect(container.querySelector('[data-testid="consent-gate-error"]')).toBeTruthy());
		expect(container.querySelector('[data-testid="consent-gate-accept"]')).toBeTruthy();
	});
});
