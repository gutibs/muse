<script lang="ts">
	let {
		value = $bindable(0),
		max = 5,
		variant = 'price',
		label = '',
	}: {
		value: number;
		max?: number;
		variant?: 'price' | 'quality';
		label?: string;
	} = $props();

	let levels = $derived(Array.from({ length: max }, (_, i) => i + 1));
</script>

<div>
	{#if label}
		<span class="mb-2 block text-sm font-medium text-ink-light">{label}</span>
	{/if}
	<div class="flex w-full gap-2">
		{#each levels as level}
			<button
				type="button"
				class="flex min-h-11 flex-1 items-center justify-center gap-0 rounded-card transition-all active:scale-95 {level <= value ? 'bg-jade text-white shadow-card' : 'bg-white text-ink-muted shadow-card'}"
				onclick={() => (value = value === level ? 0 : level)}
				aria-label="{label} {level} of {max}"
			>
				{#if variant === 'price'}
					<span class="text-sm font-bold">{'$'.repeat(level)}</span>
				{:else}
					{#each Array(level) as _}
						<svg class="h-4 w-2.5" viewBox="0 0 10 24" fill="currentColor">
							<!-- fork: 4 tines + handle -->
							<path d="M1 1v7c0 1.1.9 2 2 2h.5v12c0 .6.4 1 1 1h1c.6 0 1-.4 1-1V10H7c1.1 0 2-.9 2-2V1H7.5v5.5c0 .3-.2.5-.5.5s-.5-.2-.5-.5V1H5.5v5.5c0 .3-.2.5-.5.5s-.5-.2-.5-.5V1H3.5v5.5c0 .3-.2.5-.5.5s-.5-.2-.5-.5V1H1z" />
						</svg>
					{/each}
				{/if}
			</button>
		{/each}
	</div>
</div>
