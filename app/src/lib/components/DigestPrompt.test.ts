import { fireEvent, render, waitFor } from '@testing-library/svelte';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import DigestPrompt from './DigestPrompt.svelte';
import * as push from '$lib/services/push.service';
import { authStore } from '$lib/stores/auth.store.svelte';

vi.mock('$lib/stores/auth.store.svelte', () => ({
	authStore: { updateProfile: vi.fn() }
}));

vi.mock('$lib/services/push.service', () => ({
	permissionState: vi.fn(),
	enable: vi.fn()
}));

/**
 * El resumen se pide desde el 2026-09-08. Lo que estos tests fijan es que las
 * dos respuestas cierren el diálogo para siempre —marcando `digestPromptSeen`—
 * y que un fallo de red NO lo cierre: si se marca visto sin haber guardado la
 * decisión, la persona nunca vuelve a ver la oferta y queda sin resumen sin
 * haber elegido eso.
 */
/** `querySelector` devuelve `Element | null` y `fireEvent` no acepta null, así
 * que sin esto no compila. De paso, cuando el elemento no está el error dice
 * cuál falta en vez de "null is not assignable". */
function pick(container: HTMLElement, id: string): Element {
	const el = container.querySelector(`[data-testid="${id}"]`);
	if (!el) throw new Error(`no está en pantalla: ${id}`);
	return el;
}

describe('DigestPrompt', () => {
	beforeEach(() => {
		vi.mocked(authStore.updateProfile).mockReset().mockResolvedValue(undefined as never);
		vi.mocked(push.permissionState).mockReset().mockResolvedValue('granted');
		vi.mocked(push.enable).mockReset().mockResolvedValue(true);
	});

	it('decir que sí enciende el resumen y no vuelve a preguntar', async () => {
		const { container } = render(DigestPrompt);

		await fireEvent.click(pick(container, 'digest-prompt-yes'));

		await waitFor(() =>
			expect(authStore.updateProfile).toHaveBeenCalledWith({
				notifyDailyDigest: true,
				digestPromptSeen: true
			})
		);
	});

	it('decir que no lo deja apagado y tampoco vuelve a preguntar', async () => {
		const { container } = render(DigestPrompt);

		await fireEvent.click(pick(container, 'digest-prompt-no'));

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

		await fireEvent.click(pick(container, 'digest-prompt-yes'));

		await waitFor(() => expect(pick(container, 'digest-prompt-error')).toBeTruthy());
		// Los botones siguen ahí: nada se marcó como visto en el servidor.
		expect(pick(container, 'digest-prompt-yes')).toBeTruthy();
	});

	it('si el teléfono bloquea las notificaciones, no se enciende nada', async () => {
		// `push.enable()` no lanza: devuelve false. Con el PATCH primero, el
		// perfil quedaba con el resumen encendido sobre un teléfono que nunca
		// iba a recibirlo, y el componente ya se había desmontado — así que no
		// había forma de avisar.
		vi.mocked(push.permissionState).mockResolvedValue('denied');
		vi.mocked(push.enable).mockResolvedValue(false);
		const { container } = render(DigestPrompt);

		await fireEvent.click(pick(container, 'digest-prompt-yes'));

		await waitFor(() => expect(pick(container, 'digest-prompt-error')).toBeTruthy());
		expect(authStore.updateProfile).not.toHaveBeenCalled();
	});

	it('decir que no nunca pide permiso de notificaciones', async () => {
		vi.mocked(push.permissionState).mockResolvedValue('denied');
		const { container } = render(DigestPrompt);

		await fireEvent.click(pick(container, 'digest-prompt-no'));

		await waitFor(() => expect(authStore.updateProfile).toHaveBeenCalled());
		expect(push.enable).not.toHaveBeenCalled();
	});
});
