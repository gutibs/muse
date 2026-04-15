<script lang="ts">
	let { value = $bindable(0) }: { value: number } = $props();
</script>

<div class="flex w-full gap-2">
	{#each [1, 2, 3, 4, 5] as heart}
		<button
			type="button"
			class="flex min-h-11 flex-1 items-center justify-center rounded-card text-2xl transition-all active:scale-95 {heart <= value ? 'bg-jade text-white shadow-card' : 'bg-white text-ink-muted shadow-card'}"
			onclick={() => (value = value === heart ? 0 : heart)}
			aria-label="Rate {heart} heart{heart > 1 ? 's' : ''}"
		>
			<svg class="h-6 w-6" viewBox="0 0 24 24" fill="currentColor"><path d="M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z"/></svg>
		</button>
	{/each}
</div>
