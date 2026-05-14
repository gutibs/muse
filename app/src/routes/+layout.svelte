<script lang="ts">
	import '../app.css';
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import AppShell from '$lib/components/AppShell.svelte';
	import { authStore } from '$lib/stores/auth.store.svelte';
	import type { Snippet } from 'svelte';

	let { children }: { children: Snippet } = $props();

	$effect(() => {
		authStore.init();
	});

	// Hardware back button (Android via Capacitor).
	// Default Capacitor behavior is exitApp() when WebView has no history,
	// which closes the app from /register if the user landed there directly.
	$effect(() => {
		let cleanup: (() => void) | undefined;
		(async () => {
			const { Capacitor } = await import('@capacitor/core');
			if (!Capacitor.isNativePlatform()) return;
			const { App } = await import('@capacitor/app');
			const handle = await App.addListener('backButton', ({ canGoBack }) => {
				const path = page.url.pathname;
				// Entry screens: exit the app.
				if (path === '/' || path === '/login') {
					App.exitApp();
					return;
				}
				// Register has no real history when reached from the landing.
				if (path === '/register') {
					goto('/login');
					return;
				}
				// Authenticated root: exit.
				if (path === '/home') {
					App.exitApp();
					return;
				}
				// Anywhere else: use WebView history if available, else exit.
				if (canGoBack) {
					window.history.back();
				} else {
					App.exitApp();
				}
			});
			cleanup = () => handle.remove();
		})();
		return () => cleanup?.();
	});
</script>

<AppShell>
	{@render children()}
</AppShell>
