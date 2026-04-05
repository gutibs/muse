<script lang="ts">
	import { goto } from '$app/navigation';
	import { authStore } from '$lib/stores/auth.store.svelte';

	$effect(() => {
		if (!authStore.loading) {
			goto(authStore.isAuthenticated ? '/home' : '/login', { replaceState: true });
		}
	});
</script>

<div class="flex h-full items-center justify-center bg-cream">
	<h1 class="font-serif text-3xl font-bold text-jade-dark">Muse</h1>
</div>
