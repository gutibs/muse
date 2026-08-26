import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { describe, expect, it } from 'vitest';
import translations, { LOCALES } from './i18n/translations';
import { t } from './i18n/index.svelte';

// La pantalla de Ajustes tuvo "0.1.0 (MVP)" clavado en las tres traducciones
// mientras el APK iba por V1.1.0. No es cosmético: el CLAUDE.md manda comparar
// el versionName que muestra la app contra build.gradle para descartar "tenés
// un APK viejo", y con la versión hardcodeada ese diagnóstico da falso.
// `bump-version.mjs` sincroniza build.gradle ↔ package.json; esto cierra el
// tercer lado del triángulo.

// Rutas desde el cwd de vitest (app/), no desde import.meta.url: bajo
// happy-dom la URL del módulo no tiene esquema file:.
const pkg = JSON.parse(readFileSync(resolve(process.cwd(), 'package.json'), 'utf8'));
const gradle = readFileSync(resolve(process.cwd(), 'android/app/build.gradle'), 'utf8');

describe('versión de la app', () => {
	it('inyecta la versión de package.json en build time', () => {
		expect(__APP_VERSION__).toBe(pkg.version);
	});

	it('coincide con el versionName de build.gradle', () => {
		const versionName = gradle.match(/versionName\s+"V?(\d+\.\d+\.\d+)"/)?.[1];
		expect(versionName).toBe(pkg.version);
	});

	it('ninguna traducción trae la versión hardcodeada', () => {
		for (const { code } of LOCALES) {
			const str = translations[code]['settings.appVersion'];
			expect(str, `${code} tiene que interpolar {version}`).toContain('{version}');
			expect(str, `${code} no puede traer un número de versión pegado`).not.toMatch(/\d+\.\d+\.\d+/);
		}
	});

	it('la interpolación deja la versión real en el texto que se ve', () => {
		expect(t('settings.appVersion', { version: __APP_VERSION__ })).toContain(pkg.version);
	});
});
