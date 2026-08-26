import { beforeEach, describe, expect, it, vi } from 'vitest';

// Node define el global `localStorage` sin implementarlo (ver el comentario en
// i18n/index.svelte.ts), así que en el runner hay que ponerle uno de verdad.
const store = new Map<string, string>();
vi.stubGlobal('localStorage', {
	getItem: (k: string) => store.get(k) ?? null,
	setItem: (k: string, v: string) => void store.set(k, v),
	removeItem: (k: string) => void store.delete(k),
	clear: () => store.clear()
});
import { authStore } from './auth.store.svelte';
import { authService } from '$lib/services/auth.service';

vi.mock('$lib/services/auth.service', () => ({
	authService: { changePassword: vi.fn(), getProfile: vi.fn() }
}));

describe('authStore.changePassword', () => {
	beforeEach(() => {
		localStorage.clear();
		vi.mocked(authService.changePassword).mockReset();
		vi.mocked(authService.getProfile).mockReset();
		authStore.accessToken = 'access-viejo';
		authStore.refreshToken = 'refresh-viejo';
		localStorage.setItem('muse_access_token', 'access-viejo');
		localStorage.setItem('muse_refresh_token', 'refresh-viejo');
	});

	it('stores the fresh token pair the backend returns', async () => {
		// Sin esto el usuario queda con el token que su propio cambio de
		// contraseña acaba de invalidar (CHECK_REVOKE_TOKEN), y la siguiente
		// llamada lo manda al login habiendo visto "contraseña actualizada".
		vi.mocked(authService.changePassword).mockResolvedValue({
			access: 'access-nuevo',
			refresh: 'refresh-nuevo'
		});

		await authStore.changePassword('vieja', 'Nu3va-clave-segura!');

		expect(authStore.accessToken).toBe('access-nuevo');
		expect(authStore.refreshToken).toBe('refresh-nuevo');
		expect(localStorage.getItem('muse_access_token')).toBe('access-nuevo');
		expect(localStorage.getItem('muse_refresh_token')).toBe('refresh-nuevo');
	});

	it('keeps the old tokens when the change fails', async () => {
		vi.mocked(authService.changePassword).mockRejectedValue(new Error('400'));

		await expect(authStore.changePassword('mal', 'x')).rejects.toThrow();

		expect(authStore.accessToken).toBe('access-viejo');
		expect(localStorage.getItem('muse_access_token')).toBe('access-viejo');
	});
});
