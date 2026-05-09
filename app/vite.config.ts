import { sveltekit } from '@sveltejs/kit/vite';
import tailwindcss from '@tailwindcss/vite';
import { defineConfig } from 'vitest/config';

export default defineConfig({
	plugins: [tailwindcss(), sveltekit()],
	envDir: '.',
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
});
