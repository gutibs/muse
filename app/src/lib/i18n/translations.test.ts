import { describe, expect, it } from 'vitest';
import translations, { LOCALES } from './translations';

/**
 * Los tres idiomas se editan a mano y en bloques separados de 450 líneas.
 * `t()` cae al inglés cuando una clave falta, así que una traducción olvidada
 * no rompe nada: la pantalla sale en inglés en medio del castellano y nadie se
 * entera hasta que un usuario lo reporta. Esto es esa convención convertida en
 * check, que es lo que el CLAUDE.md pide para las reglas que importan.
 */
describe('translations', () => {
	const reference = Object.keys(translations.en).sort();

	for (const { code } of LOCALES.filter((l) => l.code !== 'en')) {
		it(`${code} covers every key that en has`, () => {
			const missing = reference.filter((key) => !(key in translations[code]));
			expect(missing, `sin traducir en ${code}`).toEqual([]);
		});

		it(`${code} has no key that en does not`, () => {
			// Una clave de más suele ser un rename a medio hacer: la vieja
			// quedó en un idioma y la nueva se agregó en otro.
			const extra = Object.keys(translations[code]).filter((key) => !(key in translations.en));
			expect(extra, `sobran en ${code}`).toEqual([]);
		});

		it(`${code} leaves no value empty`, () => {
			const empty = Object.entries(translations[code])
				.filter(([, value]) => !value.trim())
				.map(([key]) => key);
			expect(empty, `vacías en ${code}`).toEqual([]);
		});
	}
});
