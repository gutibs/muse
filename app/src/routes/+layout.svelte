<script lang="ts">
	import '../app.css';
	import AppShell from '$lib/components/AppShell.svelte';
	import { authStore } from '$lib/stores/auth.store.svelte';
	import type { Snippet } from 'svelte';

	let { children }: { children: Snippet } = $props();

	$effect(() => {
		authStore.init();
	});
</script>

<AppShell>
	{@render children()}
</AppShell>
