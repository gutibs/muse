import translations, { type Locale, LOCALES } from './translations';

export { LOCALES, type Locale };

const LOCALE_KEY = 'muse_locale';

class I18n {
	locale = $state<Locale>('en');

	constructor() {
		if (typeof localStorage !== 'undefined') {
			const saved = localStorage.getItem(LOCALE_KEY) as Locale | null;
			if (saved && translations[saved]) {
				this.locale = saved;
				return;
			}
		}
		if (typeof navigator !== 'undefined') {
			const langs = navigator.languages?.length ? navigator.languages : [navigator.language];
			for (const raw of langs) {
				const code = raw?.toLowerCase().split('-')[0] as Locale;
				if (code && translations[code]) {
					this.locale = code;
					return;
				}
			}
		}
	}

	setLocale(locale: Locale) {
		this.locale = locale;
		if (typeof localStorage !== 'undefined') {
			localStorage.setItem(LOCALE_KEY, locale);
		}
	}

	t(key: string, params?: Record<string, string>): string {
		let str = translations[this.locale]?.[key] ?? translations.en[key] ?? key;
		if (params) {
			for (const [k, v] of Object.entries(params)) {
				str = str.replace(`{${k}}`, v);
			}
		}
		return str;
	}
}

export const i18n = new I18n();
export function t(key: string, params?: Record<string, string>): string {
	return i18n.t(key, params);
}
