<script lang="ts">
	import { i18n, LOCALES } from '$lib/i18n/index.svelte';
	import { t } from '$lib/i18n/index.svelte';
	import type { Snippet } from 'svelte';

	let { children }: { children: Snippet } = $props();

	// Inline SVG flags (no network) — mirrors LanguagePicker.svelte.
	const FLAGS: Record<string, string> = {
		en: 'data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 60 30"><clipPath id="a"><rect width="60" height="30"/></clipPath><g clip-path="url(%23a)"><rect width="60" height="30" fill="%23012169"/><path d="M0 0l60 30M60 0L0 30" stroke="%23fff" stroke-width="6"/><path d="M0 0l60 30M60 0L0 30" stroke="%23C8102E" stroke-width="4" clip-path="url(%23a)"/><path d="M30 0v30M0 15h60" stroke="%23fff" stroke-width="10"/><path d="M30 0v30M0 15h60" stroke="%23C8102E" stroke-width="6"/></g></svg>',
		es: 'data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 750 500"><rect width="750" height="500" fill="%23c60b1e"/><rect width="750" height="250" y="125" fill="%23ffc400"/></svg>',
		it: 'data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 3 2"><rect width="1" height="2" fill="%23009246"/><rect width="1" height="2" x="1" fill="%23fff"/><rect width="1" height="2" x="2" fill="%23ce2b37"/></svg>',
	};

	function back() {
		if (typeof history !== 'undefined' && history.length > 1) {
			history.back();
		} else {
			location.href = '/profile';
		}
	}
</script>

<div class="flex h-full flex-col bg-cream">
	<header class="flex shrink-0 items-center gap-2 border-b border-cream-dark bg-cream px-3 py-3">
		<button
			onclick={back}
			aria-label={t('legal.back')}
			class="flex min-h-11 min-w-11 items-center justify-center rounded-full text-ink-light active:bg-cream-dark active:opacity-70"
		>
			<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M19 12H5"/><path d="M12 19l-7-7 7-7"/></svg>
		</button>
		<h1 class="text-base font-semibold text-ink">{t('legal.section')}</h1>

		<div class="ml-auto flex gap-1">
			{#each LOCALES as loc (loc.code)}
				{@const active = i18n.locale === loc.code}
				<button
					type="button"
					onclick={() => i18n.setLocale(loc.code)}
					aria-pressed={active}
					aria-label={loc.label}
					class="flex min-h-11 min-w-11 items-center justify-center rounded-button p-1.5 active:scale-95
						{active ? 'border-2 border-jade bg-white' : 'border-2 border-transparent'}"
				>
					<img src={FLAGS[loc.code]} alt={loc.code.toUpperCase()} class="h-4 w-6 rounded-sm object-cover" />
				</button>
			{/each}
		</div>
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
