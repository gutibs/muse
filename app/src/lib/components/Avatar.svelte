<script lang="ts">
	let {
		src = null,
		name = '',
		size = 40,
	}: {
		src?: string | null;
		name?: string;
		size?: number;
	} = $props();

	let initials = $derived(
		name
			? name
					.split(' ')
					.slice(0, 2)
					.map((w) => w[0])
					.join('')
					.toUpperCase()
			: '?'
	);
</script>

{#if src}
	<img
		{src}
		alt={name}
		class="rounded-full object-cover"
		style="width: {size}px; height: {size}px;"
	/>
{:else}
	<div
		class="flex items-center justify-center rounded-full bg-jade font-semibold text-white"
		style="width: {size}px; height: {size}px; font-size: {size * 0.4}px;"
	>
		{initials}
	</div>
{/if}
