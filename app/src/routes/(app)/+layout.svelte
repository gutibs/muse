<script lang="ts">
	import { goto } from '$app/navigation';
	import BottomNav from '$lib/components/BottomNav.svelte';
	import { authStore } from '$lib/stores/auth.store.svelte';
	import type { Snippet } from 'svelte';

	let { children }: { children: Snippet } = $props();

	$effect(() => {
		if (!authStore.loading && !authStore.isAuthenticated) {
			goto('/login', { replaceState: true });
		}
	});
</script>

{#if authStore.loading}
	<div class="flex h-full items-center justify-center bg-cream">
		<h1 class="font-serif text-3xl font-bold text-jade-dark">Muse</h1>
	</div>
{:else if authStore.isAuthenticated}
	<div class="flex h-full flex-col bg-cream">
		<main class="flex-1 overflow-y-auto">
			{@render children()}
		</main>
		<BottomNav />
	</div>
{/if}
