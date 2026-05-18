<script lang="ts">
	import type { Snippet } from 'svelte';

	let { children }: { children: Snippet } = $props();

	function back() {
		if (typeof history !== 'undefined' && history.length > 1) {
			history.back();
		} else {
			location.href = '/profile';
		}
	}
</script>

<div class="flex h-full flex-col bg-cream">
	<header
		class="flex shrink-0 items-center gap-2 border-b border-cream-dark bg-cream px-3 py-3"
	>
		<button
			onclick={back}
			aria-label="Back"
			class="flex min-h-11 min-w-11 items-center justify-center rounded-full text-ink-light active:bg-cream-dark active:opacity-70"
		>
			<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M19 12H5"/><path d="M12 19l-7-7 7-7"/></svg>
		</button>
		<h1 class="text-base font-semibold text-ink">Legal</h1>
	</header>

	<main class="flex-1 overflow-y-auto px-5 py-5">
		<div class="mx-auto w-full max-w-prose">
			{@render children()}
		</div>
	</main>
</div>

<style>
	:global(.legal-doc h2) {
		font-family: ui-serif, Georgia, serif;
		font-size: 1.5rem;
		font-weight: 700;
		color: #1a4d3e;
		margin: 0 0 0.5rem;
	}
	:global(.legal-doc h3) {
		font-size: 1rem;
		font-weight: 600;
		color: #1a1a1a;
		margin: 1.5rem 0 0.5rem;
	}
	:global(.legal-doc p) {
		font-size: 0.95rem;
		line-height: 1.6;
		color: #3a3a3a;
		margin: 0 0 0.75rem;
	}
	:global(.legal-doc ul) {
		padding-left: 1.25rem;
		margin: 0 0 0.75rem;
	}
	:global(.legal-doc li) {
		font-size: 0.95rem;
		line-height: 1.6;
		color: #3a3a3a;
		margin-bottom: 0.25rem;
	}
	:global(.legal-doc a) {
		color: #1a4d3e;
		text-decoration: underline;
	}
	:global(.legal-doc .meta) {
		font-size: 0.8rem;
		color: #888;
		margin: 0 0 1.25rem;
	}
	:global(.legal-doc .nav-card) {
		display: block;
		padding: 0.85rem 1rem;
		background: #fff;
		border-radius: 14px;
		box-shadow: 0 1px 3px rgba(0,0,0,0.04);
		margin-bottom: 0.5rem;
		color: #1a1a1a;
		text-decoration: none;
		font-size: 0.95rem;
		font-weight: 500;
	}
	:global(.legal-doc .nav-card:active) {
		opacity: 0.7;
	}
</style>
