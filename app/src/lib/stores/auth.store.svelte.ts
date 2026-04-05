import { goto } from '$app/navigation';
import { initApiAuth } from '$lib/services/api.service';
import { authService } from '$lib/services/auth.service';
import type { Profile } from '$lib/types';

const TOKEN_KEY = 'muse_access_token';
const REFRESH_KEY = 'muse_refresh_token';

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

		if (!access || !refresh) {
			this.loading = false;
			return;
		}

		this.accessToken = access;
		this.refreshToken = refresh;

		try {
			this.user = await authService.getProfile();
		} catch {
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

	async register(email: string, password: string, displayName?: string) {
		const result = await authService.register({ email, password, displayName });
		this.accessToken = result.tokens.access;
		this.refreshToken = result.tokens.refresh;
		localStorage.setItem(TOKEN_KEY, result.tokens.access);
		localStorage.setItem(REFRESH_KEY, result.tokens.refresh);
		this.user = result.user;
	}

	async updateProfile(data: Partial<Pick<Profile, 'displayName' | 'bio' | 'city'>>) {
		this.user = await authService.updateProfile(data);
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
