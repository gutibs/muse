<script lang="ts">
	import type { Tag } from '$lib/types';
	import { axisLabel, groupByAxis, tagLabel } from '$lib/utils/taxonomy';

	let {
		tags = [],
		selected = $bindable([]),
		grouped = false,
		readonly = false,
	}: {
		tags: Tag[];
		/** Ids seleccionados. Ignorado con `readonly`. */
		selected?: number[];
		/** Reparte las etiquetas en vibe / occasion / scene, con su título. */
		grouped?: boolean;
		/** Sólo muestra. Para pintar las etiquetas que ya tiene un pin. */
		readonly?: boolean;
	} = $props();

	let groups = $derived(grouped ? groupByAxis(tags) : [{ kind: null, tags }]);

	function toggle(id: number) {
		selected = selected.includes(id) ? selected.filter((s) => s !== id) : [...selected, id];
	}

	function countFor(group: Tag[]): number {
		return group.filter((tag) => selected.includes(tag.id)).length;
	}
</script>

<div class="flex flex-col gap-4">
	{#each groups as group (group.kind ?? 'all')}
		<div class="flex flex-col gap-2">
			{#if group.kind}
				<div class="flex items-baseline justify-between">
					<span class="text-sm font-medium text-ink-light">{axisLabel(group.kind)}</span>
					{#if !readonly && countFor(group.tags) > 0}
						<span class="text-xs text-ink-muted">{countFor(group.tags)}</span>
					{/if}
				</div>
			{/if}
			<div class="flex flex-wrap gap-2">
				{#each group.tags as tag (tag.id)}
					{#if readonly}
						<span class="rounded-chip bg-cream-dark px-3 py-1 text-xs text-ink-light">
							{tagLabel(tag)}
						</span>
					{:else}
						<button
							type="button"
							aria-pressed={selected.includes(tag.id)}
							onclick={() => toggle(tag.id)}
							class="min-h-11 rounded-chip px-3.5 text-sm transition-colors active:scale-[0.98]
								{selected.includes(tag.id)
								? 'bg-jade text-white'
								: 'bg-cream-dark text-ink-light'}"
						>
							{tagLabel(tag)}
						</button>
					{/if}
				{/each}
			</div>
		</div>
	{/each}
</div>
