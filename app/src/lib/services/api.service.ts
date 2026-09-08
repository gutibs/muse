import { i18n } from '$lib/i18n/index.svelte';
import { ApiError, AuthError, type PaginatedResponse } from '$lib/types';

const API_BASE = import.meta.env.VITE_API_BASE_URL || '/api/v1';

/**
 * Idioma en el que queremos los mensajes de error del backend.
 *
 * Sin esto, la API contesta siempre en inglés: sus mensajes pasan por gettext
 * y `LocaleMiddleware` los resuelve mirando este header. Un usuario con la app
 * en español leía "Current password is incorrect." al borrar su cuenta.
 */
function acceptLanguage(): Record<string, string> {
	return { 'Accept-Language': i18n.locale };
}

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

/**
 * El cuerpo de una respuesta, o `undefined` si no trae ninguno.
 *
 * No alcanza con mirar el 204: un `Response(status=201)` de DRF sin `data`
 * también llega sin cuerpo, y `json()` sobre eso tira `Unexpected end of
 * JSON input`. El cliente lo veía como fallo de red y revertía una escritura
 * que el servidor había aceptado — pasó con el primer voto de una shortlist.
 */
async function parseBody<T>(response: Response): Promise<T> {
	if (response.status === 204) return undefined as T;
	// Se mira el cuerpo y no `content-length`: ese header no viaja con
	// `Transfer-Encoding: chunked` y tampoco lo trae todo mock de test.
	const texto = await response.text();
	return (texto ? JSON.parse(texto) : undefined) as T;
}

async function request<T>(path: string, options?: RequestInit, alreadyRetried = false): Promise<T> {
	const token = getAccessToken();
	// Con un FormData adentro **no se declara Content-Type**: lo tiene que
	// escribir el navegador, porque es el único que conoce el `boundary` que
	// separa las partes. Declararlo a mano deja al servidor con un cuerpo que
	// no puede partir, y el error que devuelve no menciona la cabecera.
	const esFormulario = typeof FormData !== 'undefined' && options?.body instanceof FormData;
	const headers: Record<string, string> = {
		...(esFormulario ? {} : { 'Content-Type': 'application/json' }),
		...acceptLanguage(),
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

	return parseBody<T>(response);
}

/** Igual que `request` pero sin Authorization y sin la maquinaria de refresh:
 * un 401 acá es la respuesta del endpoint, no una sesión vencida. */
async function requestAnon<T>(path: string, options?: RequestInit): Promise<T> {
	const controller = new AbortController();
	const timeoutId = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

	let response: Response;
	try {
		response = await fetch(`${API_BASE}${path}`, {
			...options,
			signal: controller.signal,
			headers: {
				'Content-Type': 'application/json',
				...acceptLanguage(),
				...(options?.headers as Record<string, string>),
			},
		});
	} catch (fetchErr) {
		console.error('[api] anonymous fetch failed:', fetchErr);
		throw fetchErr;
	} finally {
		clearTimeout(timeoutId);
	}

	if (!response.ok) {
		const data = await response.json().catch(() => null);
		throw new ApiError(response.status, data);
	}

	return parseBody<T>(response);
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
	/**
	 * POST a un endpoint anónimo, sin mandar el token aunque haya uno guardado.
	 *
	 * DRF corre la autenticación antes que el permiso, así que una view
	 * AllowAny responde 401 igual si el header trae un token que ya no vale.
	 * Por ese camino, `post` intentaría refrescar, fallaría y haría clearAuth
	 * en medio de un flujo anónimo. Lo usa la recuperación de contraseña, que
	 * es donde la persona por definición no tiene sesión válida.
	 */
	postAnon<T>(path: string, body?: unknown, headers?: Record<string, string>): Promise<T> {
		return requestAnon<T>(path, {
			method: 'POST',
			body: body ? JSON.stringify(body) : undefined,
			headers,
		});
	},
	/**
	 * DELETE sin sesión. Lo usa la votación de shortlists: sacar el propio
	 * voto es una operación de alguien que no tiene cuenta, identificado por
	 * una clave que viaja en un header.
	 */
	deleteAnon<T>(path: string, headers?: Record<string, string>): Promise<T> {
		return requestAnon<T>(path, { method: 'DELETE', headers });
	},
	/**
	 * GET sin tocar la sesión. Mismo motivo que `postAnon`.
	 *
	 * Lo usa el chequeo de versión, que corre al arrancar: por `get` normal, un
	 * token vencido en el header haría que DRF conteste 401 —la autenticación
	 * corre antes que el permiso, incluso en una view AllowAny—, y el refresh
	 * fallido haría `clearAuth` en medio del arranque. Cerrar la sesión de
	 * alguien por consultar un número de versión sería absurdo.
	 */
	getAnon<T>(path: string): Promise<T> {
		return requestAnon<T>(path);
	},
	/**
	 * POST de un archivo. El `FormData` viaja tal cual y `request` se encarga
	 * de no pisar la cabecera que el navegador necesita escribir.
	 */
	postForm<T>(path: string, form: FormData): Promise<T> {
		return request<T>(path, { method: 'POST', body: form });
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
