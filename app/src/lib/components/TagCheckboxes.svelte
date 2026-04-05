<script lang="ts">
	import type { Tag } from '$lib/types';

	let {
		tags = [],
		selected = $bindable([]),
	}: {
		tags: Tag[];
		selected: number[];
	} = $props();

	function toggle(id: number) {
		if (selected.includes(id)) {
			selected = selected.filter((s) => s !== id);
		} else {
			selected = [...selected, id];
		}
	}
</script>

<div class="grid grid-cols-2 gap-2">
	{#each tags as tag}
		<button
			type="button"
			class="flex items-center gap-2 rounded-card px-3 py-2.5 text-left text-sm transition-colors active:scale-[0.98] {selected.includes(tag.id) ? 'bg-jade text-white' : 'bg-white text-ink-light shadow-card'}"
			onclick={() => toggle(tag.id)}
		>
			{#if selected.includes(tag.id)}
				<svg class="h-4 w-4 shrink-0" viewBox="0 0 16 16" fill="currentColor">
					<path d="M13.78 4.22a.75.75 0 0 1 0 1.06l-7.25 7.25a.75.75 0 0 1-1.06 0L2.22 9.28a.75.75 0 0 1 1.06-1.06L6 10.94l6.72-6.72a.75.75 0 0 1 1.06 0Z" />
				</svg>
			{:else}
				<div class="h-4 w-4 shrink-0 rounded border border-cream-dark"></div>
			{/if}
			<span class="truncate">{tag.name}</span>
		</button>
	{/each}
</div>
