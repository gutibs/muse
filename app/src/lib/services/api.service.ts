import { ApiError, AuthError } from '$lib/types';

const API_BASE = import.meta.env.VITE_API_BASE_URL || '/api/v1';

let getAccessToken: () => string | null = () => null;
let getRefreshToken: () => string | null = () => null;
let setTokens: (access: string, refresh: string) => void = () => {};
let clearAuth: () => void = () => {};

export function initApiAuth(config: {
	getAccessToken: () => string | null;
	getRefreshToken: () => string | null;
	setTokens: (access: string, refresh: string) => void;
	clearAuth: () => void;
}) {
	getAccessToken = config.getAccessToken;
	getRefreshToken = config.getRefreshToken;
	setTokens = config.setTokens;
	clearAuth = config.clearAuth;
}

// Refresh lock: if a refresh is in progress, all 401s wait for it
let refreshPromise: Promise<boolean> | null = null;

async function refreshAccessToken(): Promise<boolean> {
	if (refreshPromise) return refreshPromise;

	refreshPromise = (async () => {
		const refresh = getRefreshToken();
		if (!refresh) return false;

		try {
			const response = await fetch(`${API_BASE}/auth/token/refresh/`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ refresh }),
			});

			if (!response.ok) return false;

			const data = await response.json();
			setTokens(data.access, data.refresh ?? refresh);
			return true;
		} catch {
			return false;
		} finally {
			refreshPromise = null;
		}
	})();

	return refreshPromise;
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
	const token = getAccessToken();
	const headers: Record<string, string> = {
		'Content-Type': 'application/json',
		...(token ? { Authorization: `Bearer ${token}` } : {}),
	};

	const response = await fetch(`${API_BASE}${path}`, {
		...options,
		headers: { ...headers, ...(options?.headers as Record<string, string>) },
	});

	if (response.status === 401 && token) {
		const refreshed = await refreshAccessToken();
		if (refreshed) {
			return request(path, options);
		}
		clearAuth();
		throw new AuthError();
	}

	if (!response.ok) {
		const data = await response.json().catch(() => null);
		throw new ApiError(response.status, data);
	}

	if (response.status === 204) return undefined as T;
	return response.json();
}

export const api = {
	get<T>(path: string): Promise<T> {
		return request<T>(path);
	},
	post<T>(path: string, body?: unknown): Promise<T> {
		return request<T>(path, {
			method: 'POST',
			body: body ? JSON.stringify(body) : undefined,
		});
	},
	patch<T>(path: string, body: unknown): Promise<T> {
		return request<T>(path, {
			method: 'PATCH',
			body: JSON.stringify(body),
		});
	},
	put<T>(path: string, body: unknown): Promise<T> {
		return request<T>(path, {
			method: 'PUT',
			body: JSON.stringify(body),
		});
	},
	delete(path: string): Promise<void> {
		return request<void>(path, { method: 'DELETE' });
	},
};
