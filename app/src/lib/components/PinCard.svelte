<script lang="ts">
	import type { Snippet } from 'svelte';

	let {
		href,
		onclick,
		imageUrl,
		imageAlt = '',
		imageClass = 'h-28 w-24',
		contentClass = 'flex min-w-0 flex-1 flex-col justify-center gap-1 p-3',
		children,
	}: {
		/** Renders an `<a>`. Mutually exclusive with `onclick`. */
		href?: string;
		/** Renders a `<button>`. Ignored when `href` is set. */
		onclick?: () => void;
		imageUrl?: string | null;
		imageAlt?: string;
		/** Size of the thumbnail. Each screen uses its own. */
		imageClass?: string;
		/** Layout of the text column, for the screens that need a different one. */
		contentClass?: string;
		children: Snippet;
	} = $props();

	// A Google photo ref expires and starts answering 4xx: without this the card
	// showed the browser's broken-image glyph. Falling back to "no photo" reuses
	// a state every screen already draws, so nothing new has to be designed.
	let failedUrl = $state<string | null>(null);
	let showImage = $derived(Boolean(imageUrl) && imageUrl !== failedUrl);
</script>

{#snippet card()}
	{#if showImage}
		<img
			src={imageUrl}
			alt={imageAlt}
			class="{imageClass} shrink-0 object-cover"
			loading="lazy"
			onerror={() => (failedUrl = imageUrl ?? null)}
		/>
	{/if}
	<div class={contentClass}>
		{@render children()}
	</div>
{/snippet}

{#if href}
	<a {href} class="flex overflow-hidden rounded-card bg-white shadow-card active:scale-[0.98]">
		{@render card()}
	</a>
{:else if onclick}
	<button
		type="button"
		{onclick}
		class="flex w-full overflow-hidden rounded-card bg-white text-left shadow-card active:scale-[0.98]"
	>
		{@render card()}
	</button>
{:else}
	<div class="flex overflow-hidden rounded-card bg-white shadow-card">
		{@render card()}
	</div>
{/if}
