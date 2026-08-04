/**
 * Public URLs of the legal documents.
 *
 * The app deliberately does NOT carry its own copy of these texts. They used
 * to exist twice — as Svelte pages here and as HTML in the landing bundle —
 * and drifted apart: the app merged GDPR+PDPO into one page while the landing
 * kept them separate, so the policy you saw depended on whether you arrived
 * through the web or the app. One published source, consumed by both.
 *
 * As a side effect the app gets these in English, Spanish and Italian: the
 * landing pages carry all three, the in-app copies were English only.
 *
 * Absolute and hardcoded on purpose: these are published documents that live
 * at a stable address (the same one filed with the app stores), not something
 * that varies per environment. Inside Capacitor the page origin is
 * capacitor://localhost, so a relative path would resolve against the app
 * bundle and 404.
 */
const LEGAL_BASE = 'https://lovemuse.app';

export const LEGAL_URLS = {
	privacy: `${LEGAL_BASE}/privacy.html`,
	terms: `${LEGAL_BASE}/terms.html`,
	community: `${LEGAL_BASE}/community.html`,
	cookies: `${LEGAL_BASE}/cookies.html`,
	contact: `${LEGAL_BASE}/contact.html`,
} as const;
