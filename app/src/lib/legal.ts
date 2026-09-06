import { i18n } from '$lib/i18n/index.svelte';

/**
 * Public URLs of the legal documents.
 *
 * The app deliberately does NOT carry its own copy of these texts. They used
 * to exist twice — as Svelte pages here and as HTML in the landing bundle —
 * and drifted apart: the app merged GDPR+PDPO into one page while the landing
 * kept them separate, so the policy you saw depended on whether you arrived
 * through the web or the app. One published source, consumed by both.
 *
 * The landing carries all three languages, so the app gets them too — but the
 * language has to travel in the URL. The landing picks its locale from its own
 * `localStorage` and then `navigator.language`, and neither one can see the
 * app's choice: inside Capacitor the page origin is `capacitor://localhost`
 * and the landing is `https://lovemuse.app`, two separate storage origins. So
 * an APK set to Spanish opened the privacy policy in whatever language the
 * phone's browser happened to be in. `?lang=` closes that gap; `i18n.js`
 * reads it before anything else.
 *
 * Absolute and hardcoded on purpose: these are published documents that live
 * at a stable address (the same one filed with the app stores), not something
 * that varies per environment. Inside Capacitor a relative path would resolve
 * against the app bundle and 404.
 */
const LEGAL_BASE = 'https://lovemuse.app';

export type LegalDoc = 'privacy' | 'terms' | 'community' | 'cookies' | 'contact';

/**
 * URL of a legal document in the language the app is currently using.
 *
 * Read `i18n.locale` at call time on purpose: it is `$state`, so a template
 * that calls this re-runs when the user switches language and the links point
 * at the new one without a reload.
 */
export function legalUrl(doc: LegalDoc): string {
	return `${LEGAL_BASE}/${doc}.html?lang=${i18n.locale}`;
}
