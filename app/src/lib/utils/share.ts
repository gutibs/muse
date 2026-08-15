import { copyToClipboard } from './clipboard';

/**
 * Turn a possibly-relative API URL into one that works when pasted anywhere.
 *
 * Matters inside Capacitor, where `window.location.origin` is
 * `capacitor://localhost` and a relative link is useless to the recipient.
 * The backend already returns absolute URLs for shared lists (built from
 * APP_PUBLIC_URL); this covers the paths that do not.
 */
export function absoluteUrl(url: string): string {
	if (url.startsWith('http')) return url;
	if (typeof window === 'undefined') return url;
	return `${window.location.origin}${url}`;
}

export type ShareResult = 'shared' | 'copied' | 'cancelled' | 'failed';

/**
 * Share a link through the OS share sheet, falling back to the clipboard.
 *
 * Returns what actually happened so the caller can pick the right message:
 * "link copied" after a clipboard fallback is correct, but after a native
 * share it is a lie, and after the user dismissed the sheet it is worse.
 *
 * The three call sites that existed before this — two of them in the same
 * file — each had their own copy of the origin-prefixing ternary, and only
 * one of them ever tried `navigator.share`.
 */
export async function shareLink({
	url,
	title,
	text,
}: {
	url: string;
	title?: string;
	text?: string;
}): Promise<ShareResult> {
	const fullUrl = absoluteUrl(url);

	if (typeof navigator !== 'undefined' && typeof navigator.share === 'function') {
		try {
			await navigator.share({ title, text, url: fullUrl });
			return 'shared';
		} catch (err) {
			// Dismissing the sheet rejects with AbortError. That is an ordinary
			// user action, not a failure: report it as such instead of falling
			// through and copying a link they decided not to send.
			if (err instanceof Error && err.name === 'AbortError') return 'cancelled';
			// Anything else (no permission, unsupported payload) is worth the
			// clipboard fallback rather than leaving the user with nothing.
		}
	}

	return (await copyToClipboard(fullUrl)) ? 'copied' : 'failed';
}
