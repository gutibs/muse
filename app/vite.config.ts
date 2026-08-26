import { readFileSync } from 'node:fs';
import { sveltekit } from '@sveltejs/kit/vite';
import tailwindcss from '@tailwindcss/vite';
import { loadEnv } from 'vite';
import { defineConfig } from 'vitest/config';

// La versión que muestra Ajustes sale de acá, no de un string traducido:
// estuvo clavada en "0.1.0 (MVP)" mientras el APK iba por V1.1.0, y el
// diagnóstico de "¿tenés un APK viejo?" depende de que esa pantalla diga la
// verdad. `bump-version.mjs` ya sincroniza package.json con build.gradle.
const { version } = JSON.parse(readFileSync('./package.json', 'utf8'));

/**
 * La key de CARTO no se versiona: los `.env.capacitor*` sí están en el repo
 * (sus URLs son públicas y fijas), y una credencial no entra ahí. Llega por
 * entorno, distinto según qué se esté armando:
 *
 *   - APK:  VITE_CARTO_KEY=... npm run build:apk-prod
 *   - web:  build-arg de nginx/Dockerfile.aws, desde el .env del servidor
 *   - dev:  app/.env (Vite lo carga en todos los modos, este incluido)
 *
 * Todo build de distribución **falla** si falta, en vez de publicar mapas con
 * "API KEY REQUIRED" estampado sobre cada tile. CARTO responde 200 con la
 * marca encima: no hay error de runtime que lo delate, y así fue como llegó a
 * producción sin que nadie lo reportara. En el deploy el build corre antes del
 * `down`, así que este corte deja el sitio anterior intacto.
 *
 * `vite dev` queda afuera a propósito: ahí alcanza con el warning de map.ts.
 */
function assertCartoKey(mode: string, env: Record<string, string>) {
	const isDistribution = mode.startsWith('capacitor') || mode === 'production';
	if (!isDistribution || env.VITE_CARTO_KEY) return;
	const how = mode.startsWith('capacitor')
		? `    VITE_CARTO_KEY=<la key> npm run build:apk${mode.endsWith('-prod') ? '-prod' : ''}`
		: '    Cargá VITE_CARTO_KEY en el .env del servidor (lo toma el build-arg\n' +
			'    del servicio nginx en docker-compose.aws.yml).';
	throw new Error(
		`\n\nFalta VITE_CARTO_KEY para el build "${mode}".\n\n` +
			`${how}\n\n` +
			'Sin la key los mapas salen con la marca de agua de CARTO encima, y no\n' +
			'hay error en runtime que lo delate. Se pide gratis en\n' +
			'https://carto.com/basemaps/apikey/ y vive fuera del repo.\n'
	);
}

export default defineConfig(({ mode }) => {
	assertCartoKey(mode, loadEnv(mode, process.cwd(), 'VITE_'));

	return {
		plugins: [tailwindcss(), sveltekit()],
		envDir: '.',
		define: {
			__APP_VERSION__: JSON.stringify(version)
		},
		server: {
			port: 5174
		},
		test: {
			environment: 'happy-dom',
			// Pure-TS utils run in node; component smoke tests need a DOM.
			include: ['src/**/*.test.ts'],
			// Svelte 5 ships separate server/client builds. Vitest defaults to
			// the SSR resolution which trips `mount() is not available on the
			// server` — force the browser condition for client-side rendering.
			server: { deps: { inline: ['@testing-library/svelte'] } }
		},
		resolve: {
			conditions: process.env.VITEST ? ['browser'] : []
		}
	};
});
