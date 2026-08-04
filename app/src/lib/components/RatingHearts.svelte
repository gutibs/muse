<script lang="ts">
	import HeartIcon from '$lib/components/HeartIcon.svelte';

	/**
	 * Read-only rating display: five hearts, filled up to `value`.
	 *
	 * Not to be confused with RatingStars.svelte, which is the *input* used
	 * when creating or editing a pin. This one never existed, so seven route
	 * files each open-coded the same each/if/svg block.
	 *
	 * `value` is rounded, so a 4.3 average shows four filled hearts.
	 */
	let {
		value = 0,
		size = 'md',
		class: klass = '',
	}: { value?: number | null; size?: 'sm' | 'md' | 'lg'; class?: string } = $props();

	const dimensions = { sm: 'h-3 w-3', md: 'h-3.5 w-3.5', lg: 'h-4 w-4' };
	const filled = $derived(Math.round(value ?? 0));
</script>

<div class="flex text-rose-400 {klass}">
	{#each [1, 2, 3, 4, 5] as heart}
		<HeartIcon class="{dimensions[size]} {heart <= filled ? '' : 'text-cream-dark'}" />
	{/each}
</div>
