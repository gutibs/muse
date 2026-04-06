<script lang="ts">
	import { goto } from '$app/navigation';
	import MuseLogo from '$lib/components/MuseLogo.svelte';
	import { authStore } from '$lib/stores/auth.store.svelte';

	$effect(() => {
		if (!authStore.loading) {
			goto(authStore.isAuthenticated ? '/home' : '/login', { replaceState: true });
		}
	});
</script>

<div class="flex h-full flex-col items-center justify-center gap-3 bg-cream">
	<MuseLogo width={140} />
	<span class="font-serif text-2xl font-bold text-jade-dark">Muse</span>
</div>
