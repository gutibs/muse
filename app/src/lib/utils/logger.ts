/**
 * Logs an error to console.warn without rethrowing.
 *
 * Use this in catches that don't break user flow but should still be
 * visible in devtools. Typical case: optional fetches whose failure
 * yields an empty list (sharedLists, cuisines, friend pins overlay).
 *
 * The pre-commit hook check_no_console_log allows console.warn but
 * blocks raw debug-style logs. Using logSilent instead of console.warn
 * directly also gives a uniform [scope] prefix that's grep-friendly
 * in the browser DevTools console panel.
 */
export function logSilent(scope: string, err: unknown): void {
	const msg = err instanceof Error ? err.message : String(err);
	console.warn(`[${scope}]`, msg, err);
}
