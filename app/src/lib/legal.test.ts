import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { beforeEach, describe, expect, it } from 'vitest';
import { legalUrl, type LegalDoc } from './legal';
import { i18n } from './i18n/index.svelte';
import { LOCALES } from './i18n/translations';

// Probado en el APK V1.3.0 el 2026-09-06: con la app en español, los cinco
// links legales del perfil abrían en inglés. Las URLs eran constantes sin
// idioma, y la landing lo deducía de su propio localStorage y de
// navigator.language — ninguno de los dos puede ver la elección hecha en la
// app, porque el APK corre en capacitor://localhost y la landing en
// lovemuse.app. No es cosmético: son la política de privacidad y los términos,
// y el consentimiento del GDPR se apoya en que la persona los lea en su idioma.

const DOCS: LegalDoc[] = ['privacy', 'terms', 'community', 'cookies', 'contact'];

// El otro lado del contrato vive en la landing, fuera del build de la app.
// Sin esto, borrar la lectura de `?lang=` en i18n.js dejaría estos tests en
// verde con los links otra vez en inglés.
const landingI18n = readFileSync(
	resolve(process.cwd(), '../nginx/landing/i18n.js'),
	'utf8'
);

describe('URLs de los documentos legales', () => {
	beforeEach(() => {
		i18n.setLocale('en');
	});

	it('lleva el idioma actual de la app, en los tres idiomas', () => {
		expect(LOCALES.map((l) => l.code)).toEqual(['en', 'es', 'it']);
		for (const { code } of LOCALES) {
			i18n.setLocale(code);
			for (const doc of DOCS) {
				expect(legalUrl(doc)).toBe(`https://lovemuse.app/${doc}.html?lang=${code}`);
			}
		}
	});

	it('sigue el cambio de idioma sin recargar', () => {
		expect(legalUrl('privacy')).toContain('lang=en');
		i18n.setLocale('es');
		expect(legalUrl('privacy')).toContain('lang=es');
	});

	it('apunta al dominio publicado, que es el que figura en las tiendas', () => {
		for (const doc of DOCS) {
			expect(legalUrl(doc)).toMatch(/^https:\/\/lovemuse\.app\//);
		}
	});

	it('la landing lee ?lang= y le gana a localStorage y a navigator', () => {
		expect(landingI18n).toContain("get('lang')");
		const fromUrl = landingI18n.indexOf("get('lang')");
		const fromStorage = landingI18n.indexOf('localStorage.getItem(LOCALE_KEY)');
		const fromNavigator = landingI18n.indexOf('navigator.language');
		expect(fromUrl).toBeGreaterThan(-1);
		expect(fromUrl).toBeLessThan(fromStorage);
		expect(fromUrl).toBeLessThan(fromNavigator);
	});
});
