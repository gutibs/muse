import { goto } from '$app/navigation';
import { initApiAuth } from '$lib/services/api.service';
import { authService } from '$lib/services/auth.service';
import type { Profile } from '$lib/types';
import { logSilent } from '$lib/utils/logger';

const TOKEN_KEY = 'muse_access_token';
const REFRESH_KEY = 'muse_refresh_token';

function isJwtExpired(token: string): boolean {
	try {
		const payload = JSON.parse(atob(token.split('.')[1]));
		return typeof payload.exp !== 'number' || payload.exp * 1000 <= Date.now();
	} catch (err) {
		// Unparseable token in storage: treat as expired so the user is sent
		// to login rather than looping on a broken credential. Logged because
		// a corrupt token is an anomaly worth seeing, not a normal state.
		logSilent('auth:jwtParse', err);
		return true;
	}
}

class AuthStore {
	user = $state<Profile | null>(null);
	accessToken = $state<string | null>(null);
	refreshToken = $state<string | null>(null);
	loading = $state(true);

	isAuthenticated = $derived(this.accessToken !== null && this.user !== null);

	constructor() {
		initApiAuth({
			getAccessToken: () => this.accessToken,
			getRefreshToken: () => this.refreshToken,
			setTokens: (access, refresh) => {
				this.accessToken = access;
				this.refreshToken = refresh;
				localStorage.setItem(TOKEN_KEY, access);
				localStorage.setItem(REFRESH_KEY, refresh);
			},
			clearAuth: () => this.logout(),
		});
	}

	async init() {
		const access = localStorage.getItem(TOKEN_KEY);
		const refresh = localStorage.getItem(REFRESH_KEY);

		// No tokens at all → not logged in, no need to call backend
		if (!access || !refresh) {
			this.loading = false;
			return;
		}

		// Refresh token expired → can't recover, clear silently
		if (isJwtExpired(refresh)) {
			this.clearTokens();
			this.loading = false;
			return;
		}

		this.accessToken = access;
		this.refreshToken = refresh;

		try {
			this.user = await authService.getProfile();
		} catch (err) {
			// This is the path behind every "it logged me out on its own"
			// report: the stored token was rejected or the profile call
			// failed. It left no trace at all before.
			logSilent('auth:init:getProfile', err);
			this.clearTokens();
		}

		this.loading = false;
	}

	async login(email: string, password: string) {
		const tokens = await authService.login({ username: email, password });
		this.accessToken = tokens.access;
		this.refreshToken = tokens.refresh;
		localStorage.setItem(TOKEN_KEY, tokens.access);
		localStorage.setItem(REFRESH_KEY, tokens.refresh);
		this.user = await authService.getProfile();
	}

	async register(
		email: string,
		password: string,
		acceptPrivacy: boolean,
		displayName?: string
	) {
		const result = await authService.register({
			email,
			password,
			displayName,
			acceptPrivacy
		});
		this.accessToken = result.tokens.access;
		this.refreshToken = result.tokens.refresh;
		localStorage.setItem(TOKEN_KEY, result.tokens.access);
		localStorage.setItem(REFRESH_KEY, result.tokens.refresh);
		this.user = result.user;
	}

	/** Cambia la contraseña y se queda con el par de tokens que devuelve el
	 * backend. Sin guardarlo, el usuario queda con el token que su propio
	 * cambio acaba de invalidar: vería "contraseña actualizada" y la llamada
	 * siguiente lo mandaría al login. Las otras sesiones sí se cierran. */
	async changePassword(currentPassword: string, newPassword: string) {
		const tokens = await authService.changePassword(currentPassword, newPassword);
		this.accessToken = tokens.access;
		this.refreshToken = tokens.refresh;
		localStorage.setItem(TOKEN_KEY, tokens.access);
		localStorage.setItem(REFRESH_KEY, tokens.refresh);
	}

	async updateProfile(data: import('$lib/services/auth.service').ProfileUpdatePayload) {
		this.user = await authService.updateProfile(data);
	}

	/**
	 * Refetch the profile (including server-computed stats). Called from
	 * pages that need fresh stats — e.g. profile/+page.svelte mount, after
	 * the user added/edited/deleted pins from another route. Stats live
	 * in `Profile.get_stats` on the backend (accounts/serializers.py).
	 */
	async refreshUser() {
		if (!this.accessToken) return;
		this.user = await authService.getProfile();
	}

	logout() {
		this.clearTokens();
		goto('/login');
	}

	private clearTokens() {
		this.user = null;
		this.accessToken = null;
		this.refreshToken = null;
		localStorage.removeItem(TOKEN_KEY);
		localStorage.removeItem(REFRESH_KEY);
	}
}

export const authStore = new AuthStore();
