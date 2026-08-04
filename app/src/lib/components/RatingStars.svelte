<script lang="ts">
	import HeartIcon from '$lib/components/HeartIcon.svelte';

	// Rating *input* (tap to set). The read-only display is RatingHearts.
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
			<HeartIcon class="h-6 w-6" />
		</button>
	{/each}
</div>
