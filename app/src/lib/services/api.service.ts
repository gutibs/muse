import { ApiError, AuthError, type PaginatedResponse } from '$lib/types';

const API_BASE = import.meta.env.VITE_API_BASE_URL || '/api/v1';

// Sin VITE_API_BASE_URL, API_BASE queda relativo y en desarrollo eso significa
// pedirle la API al dev server de Vite: 404 en todo, y la UI sólo muestra
// "Something went wrong". Vite lee los env desde `app/`, así que el archivo que
// falta es `app/.env` — no el de la raíz del repo, aunque la variable esté ahí.
if (import.meta.env.DEV && !import.meta.env.VITE_API_BASE_URL) {
	console.warn(
		'[muse] Falta VITE_API_BASE_URL: la API se va a pedir a este mismo host y todo va a fallar.\n' +
			'       Arreglo: cp app/.env.example app/.env  (y reiniciar vite)'
	);
}

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

		const controller = new AbortController();
		const timeoutId = setTimeout(() => controller.abort(), 10000);
		try {
			const response = await fetch(`${API_BASE}/auth/token/refresh/`, {
				method: 'POST',
				signal: controller.signal,
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ refresh }),
			});

			if (!response.ok) {
				console.warn('[api] refresh failed:', response.status);
				return false;
			}

			const data = await response.json();
			setTokens(data.access, data.refresh ?? refresh);
			return true;
		} catch (err) {
			console.warn('[api] refresh error:', err);
			return false;
		} finally {
			clearTimeout(timeoutId);
			refreshPromise = null;
		}
	})();

	return refreshPromise;
}

const REQUEST_TIMEOUT_MS = 15000;

async function request<T>(path: string, options?: RequestInit, alreadyRetried = false): Promise<T> {
	const token = getAccessToken();
	const headers: Record<string, string> = {
		'Content-Type': 'application/json',
		...(token ? { Authorization: `Bearer ${token}` } : {}),
	};

	const url = `${API_BASE}${path}`;

	const controller = new AbortController();
	const timeoutId = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

	let response: Response;
	try {
		response = await fetch(url, {
			...options,
			signal: controller.signal,
			headers: { ...headers, ...(options?.headers as Record<string, string>) },
		});
	} catch (fetchErr) {
		console.error('[api] fetch failed:', fetchErr);
		throw fetchErr;
	} finally {
		clearTimeout(timeoutId);
	}

	if (response.status === 401 && token && !alreadyRetried) {
		const refreshed = await refreshAccessToken();
		if (refreshed) {
			return request(path, options, true);
		}
		clearAuth();
		throw new AuthError();
	}

	if (response.status === 401 && alreadyRetried) {
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

/** Max pages `getAll` will walk before giving up. At PAGE_SIZE=20 that is
 * 2000 rows — far past any list a person actually has, and a guard against
 * looping forever if the API ever returns a `next` that points at itself. */
const MAX_PAGES = 100;

export const api = {
	get<T>(path: string): Promise<T> {
		return request<T>(path);
	},

	/**
	 * Follow `next` until the API runs out of pages and return every row.
	 *
	 * The backend paginates at 20. Before this existed, three screens read
	 * `res.results` and stopped there: the map drew at most 20 markers while
	 * the profile announced the real total next to it, and the restaurant
	 * screen looked for your own pin inside the first page only — so with 21+
	 * pins a place you had already pinned offered "add pin" and the backend
	 * answered 409.
	 *
	 * Use it when the screen genuinely needs the whole set (a map, a filter, a
	 * count). For long scrollable lists prefer real infinite scroll, the way
	 * the feed does it.
	 */
	async getAll<T>(path: string): Promise<T[]> {
		const separator = path.includes('?') ? '&' : '?';
		const rows: T[] = [];
		let page: number | null = 1;

		for (let i = 0; page !== null && i < MAX_PAGES; i++) {
			const res: PaginatedResponse<T> = await request<PaginatedResponse<T>>(
				`${path}${separator}page=${page}`
			);
			rows.push(...res.results);
			// DRF returns `next` as an absolute URL built from the request host,
			// which is not the host we call from inside Capacitor. Take the page
			// number out of it and rebuild the path ourselves instead.
			page = res.next ? Number(new URL(res.next).searchParams.get('page')) || null : null;
		}
		return rows;
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
	/** `body` is only used by account deletion, which re-checks the password. */
	delete(path: string, body?: unknown): Promise<void> {
		return request<void>(path, {
			method: 'DELETE',
			body: body ? JSON.stringify(body) : undefined,
		});
	},
};
