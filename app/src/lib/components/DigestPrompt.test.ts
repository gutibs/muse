import { fireEvent, render, waitFor } from '@testing-library/svelte';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import DigestPrompt from './DigestPrompt.svelte';
import { authStore } from '$lib/stores/auth.store.svelte';

vi.mock('$lib/stores/auth.store.svelte', () => ({
	authStore: { updateProfile: vi.fn() }
}));

vi.mock('$lib/services/push.service', () => ({
	permissionState: vi.fn().mockResolvedValue('granted'),
	enable: vi.fn()
}));

/**
 * El resumen se pide desde el 2026-09-08. Lo que estos tests fijan es que las
 * dos respuestas cierren el diálogo para siempre —marcando `digestPromptSeen`—
 * y que un fallo de red NO lo cierre: si se marca visto sin haber guardado la
 * decisión, la persona nunca vuelve a ver la oferta y queda sin resumen sin
 * haber elegido eso.
 */
describe('DigestPrompt', () => {
	beforeEach(() => {
		vi.mocked(authStore.updateProfile).mockReset().mockResolvedValue(undefined as never);
	});

	it('decir que sí enciende el resumen y no vuelve a preguntar', async () => {
		const { container } = render(DigestPrompt);

		await fireEvent.click(container.querySelector('[data-testid="digest-prompt-yes"]'));

		await waitFor(() =>
			expect(authStore.updateProfile).toHaveBeenCalledWith({
				notifyDailyDigest: true,
				digestPromptSeen: true
			})
		);
	});

	it('decir que no lo deja apagado y tampoco vuelve a preguntar', async () => {
		const { container } = render(DigestPrompt);

		await fireEvent.click(container.querySelector('[data-testid="digest-prompt-no"]'));

		await waitFor(() =>
			expect(authStore.updateProfile).toHaveBeenCalledWith({
				notifyDailyDigest: false,
				digestPromptSeen: true
			})
		);
	});

	it('si no se pudo guardar, lo dice y la oferta sigue en pie', async () => {
		vi.mocked(authStore.updateProfile).mockRejectedValue(new Error('sin red'));
		const { container } = render(DigestPrompt);

		await fireEvent.click(container.querySelector('[data-testid="digest-prompt-yes"]'));

		await waitFor(() => expect(container.querySelector('[data-testid="digest-prompt-error"]')).toBeTruthy());
		// Los botones siguen ahí: nada se marcó como visto en el servidor.
		expect(container.querySelector('[data-testid="digest-prompt-yes"]')).toBeTruthy();
	});
});
