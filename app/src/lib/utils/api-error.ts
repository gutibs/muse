import { ApiError } from '$lib/types';

/**
 * Pulls the first human-readable error string out of a DRF validation response.
 * DRF returns shapes like { email: ["already exists"] } or { detail: "..." }.
 */
export function extractFirstDrfError(err: unknown, fallback = 'Something went wrong. Please try again.'): string {
	if (!(err instanceof ApiError) || !err.data) return fallback;
	const data = err.data as Record<string, unknown>;
	const keys = Object.keys(data);
	if (keys.length === 0) return fallback;
	const first = data[keys[0]];
	if (Array.isArray(first)) {
		const msg = first[0];
		return typeof msg === 'string' ? msg : fallback;
	}
	return typeof first === 'string' ? first : fallback;
}
