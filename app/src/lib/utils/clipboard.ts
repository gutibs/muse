import { logSilent } from '$lib/utils/logger';

export async function copyToClipboard(text: string): Promise<boolean> {
	if (typeof navigator !== 'undefined' && navigator.clipboard?.writeText) {
		try {
			await navigator.clipboard.writeText(text);
			return true;
		} catch (err) {
			// Denied permission or insecure context — fall through to the
			// legacy fallback. Logged because "the copy button does nothing"
			// is otherwise impossible to diagnose from a user report.
			logSilent('clipboard:modern', err);
		}
	}
	if (typeof document === 'undefined') return false;
	try {
		const textarea = document.createElement('textarea');
		textarea.value = text;
		textarea.setAttribute('readonly', '');
		textarea.style.position = 'fixed';
		textarea.style.opacity = '0';
		textarea.style.pointerEvents = 'none';
		document.body.appendChild(textarea);
		textarea.select();
		textarea.setSelectionRange(0, text.length);
		const ok = document.execCommand('copy');
		document.body.removeChild(textarea);
		return ok;
	} catch (err) {
		logSilent('clipboard:legacy', err);
		return false;
	}
}
