<script lang="ts">
	import type { Snippet } from 'svelte';
	import { t } from '$lib/i18n/index.svelte';
	import { trackVisibility } from '$lib/utils/track-visibility';

	let {
		href,
		onclick,
		onVisible,
		closed = false,
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
		/**
		 * Se llama una vez cuando la tarjeta estuvo de verdad en pantalla.
		 * La tarjeta no sabe qué se hace con eso: la pantalla decide si lo
		 * cuenta y con qué etiqueta.
		 */
		onVisible?: () => void;
		/**
		 * El lugar cerró. Se marca en la tarjeta porque es donde la gente ve
		 * sus propios pins: sin esto, un "quiero ir" a un lugar cerrado se ve
		 * igual que cualquier otro.
		 */
		closed?: boolean;
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
		{#if closed}
			<span class="mt-0.5 inline-flex w-fit rounded-full bg-blush/10 px-2 py-0.5 text-[10px] font-medium uppercase tracking-wide text-blush">
				{t('restaurant.closed')}
			</span>
		{/if}
	</div>
{/snippet}

{#if href}
	<a
		{href}
		use:trackVisibility={{ onVisible }}
		class="flex overflow-hidden rounded-card bg-white shadow-card active:scale-[0.98]"
	>
		{@render card()}
	</a>
{:else if onclick}
	<button
		type="button"
		{onclick}
		use:trackVisibility={{ onVisible }}
		class="flex w-full overflow-hidden rounded-card bg-white text-left shadow-card active:scale-[0.98]"
	>
		{@render card()}
	</button>
{:else}
	<div use:trackVisibility={{ onVisible }} class="flex overflow-hidden rounded-card bg-white shadow-card">
		{@render card()}
	</div>
{/if}
