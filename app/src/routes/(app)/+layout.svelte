<script lang="ts">
	import { goto } from '$app/navigation';
	import BottomNav from '$lib/components/BottomNav.svelte';
	import ConsentGate from '$lib/components/ConsentGate.svelte';
	import DigestPrompt from '$lib/components/DigestPrompt.svelte';
	import { authStore } from '$lib/stores/auth.store.svelte';
	import type { Snippet } from 'svelte';

	let { children }: { children: Snippet } = $props();

	// Primero lo legal: hasta que la cuenta no tenga constancia de haber
	// aceptado, no se le pide nada más.
	const faltaConsentir = $derived((authStore.user?.pendingPolicies?.length ?? 0) > 0);

	// El resumen se ofrece cuando hay de quién resumir. Un solo flag cubre los
	// dos casos que parecen distintos y son el mismo: a quien se registra
	// ahora le aparece al hacer su primer amigo, y a quien ya tenía cuenta al
	// abrir la app, porque sus amigos ya existen.
	const ofrecerResumen = $derived(
		!faltaConsentir &&
			authStore.user !== null &&
			!authStore.user.digestPromptSeen &&
			(authStore.user.stats?.friendCount ?? 0) > 0
	);

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

	{#if faltaConsentir}
		<ConsentGate />
	{:else if ofrecerResumen}
		<DigestPrompt />
	{/if}
{/if}
