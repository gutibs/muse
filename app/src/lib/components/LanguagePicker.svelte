<script lang="ts">
	import { i18n, LOCALES } from '$lib/i18n/index.svelte';

	const FLAGS: Record<string, string> = {
		en: 'data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 60 30"><clipPath id="a"><rect width="60" height="30"/></clipPath><g clip-path="url(%23a)"><rect width="60" height="30" fill="%23012169"/><path d="M0 0l60 30M60 0L0 30" stroke="%23fff" stroke-width="6"/><path d="M0 0l60 30M60 0L0 30" stroke="%23C8102E" stroke-width="4" clip-path="url(%23a)"/><path d="M30 0v30M0 15h60" stroke="%23fff" stroke-width="10"/><path d="M30 0v30M0 15h60" stroke="%23C8102E" stroke-width="6"/></g></svg>',
		es: 'data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 750 500"><rect width="750" height="500" fill="%23c60b1e"/><rect width="750" height="250" y="125" fill="%23ffc400"/></svg>',
		it: 'data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 3 2"><rect width="1" height="2" fill="%23009246"/><rect width="1" height="2" x="1" fill="%23fff"/><rect width="1" height="2" x="2" fill="%23ce2b37"/></svg>',
	};
</script>

<div class="flex gap-2">
	{#each LOCALES as loc}
		<button
			type="button"
			onclick={() => i18n.setLocale(loc.code)}
			class="flex flex-1 items-center justify-center gap-2 rounded-card py-2.5 text-sm font-medium active:scale-95
				{i18n.locale === loc.code ? 'bg-jade text-white shadow-card' : 'bg-white text-ink shadow-card'}"
		>
			<img src={FLAGS[loc.code]} alt={loc.label} class="h-4 w-6 rounded-sm object-cover" />
			<span>{loc.label}</span>
		</button>
	{/each}
</div>
