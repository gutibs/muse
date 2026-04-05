<script lang="ts">
	let { value = $bindable(0) }: { value: number } = $props();
</script>

<div class="flex w-full gap-2">
	{#each [1, 2, 3, 4, 5] as star}
		<button
			type="button"
			class="flex min-h-11 flex-1 items-center justify-center rounded-card text-2xl transition-all active:scale-95 {star <= value ? 'bg-jade text-white shadow-card' : 'bg-white text-ink-muted shadow-card'}"
			onclick={() => (value = value === star ? 0 : star)}
			aria-label="Rate {star} star{star > 1 ? 's' : ''}"
		>
			&#9733;
		</button>
	{/each}
</div>
