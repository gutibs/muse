<script lang="ts">
	import type { Snippet } from 'svelte';

	let {
		title,
		message,
		children,
	}: {
		title: string;
		message: string;
		children?: Snippet;
	} = $props();
</script>

<div class="flex flex-col items-center justify-center px-6 py-12 text-center">
	<h3 class="font-serif text-lg font-semibold text-ink">{title}</h3>
	<p class="mt-1 text-sm text-ink-muted">{message}</p>
	{#if children}
		<div class="mt-4">
			{@render children()}
		</div>
	{/if}
</div>
