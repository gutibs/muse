<script lang="ts">
	import { t } from '$lib/i18n/index.svelte';
	import type { Tag } from '$lib/types';
	import { axisLabel, groupByAxis, tagLabel } from '$lib/utils/taxonomy';

	let {
		tags = [],
		selected = $bindable([]),
		grouped = false,
		readonly = false,
		suggested = [],
	}: {
		tags: Tag[];
		/** Ids seleccionados. Ignorado con `readonly`. */
		selected?: number[];
		/** Reparte las etiquetas en vibe / occasion / scene, con su título. */
		grouped?: boolean;
		/** Sólo muestra. Para pintar las etiquetas que ya tiene un pin. */
		readonly?: boolean;
		/**
		 * Slugs que el sistema propuso, no que el usuario eligió. Se marcan
		 * distinto para que se vea que es una sugerencia: si se confunde con
		 * una elección propia, el usuario termina publicando algo que nunca
		 * dijo.
		 */
		suggested?: string[];
	} = $props();

	let groups = $derived(grouped ? groupByAxis(tags) : [{ kind: null, tags }]);

	function toggle(id: number) {
		selected = selected.includes(id) ? selected.filter((s) => s !== id) : [...selected, id];
	}

	function isSuggested(tag: Tag): boolean {
		return suggested.includes(tag.slug) && selected.includes(tag.id);
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
							data-suggested={isSuggested(tag) ? 'true' : undefined}
							onclick={() => toggle(tag.id)}
							class="min-h-11 rounded-chip px-3.5 text-sm transition-colors active:scale-[0.98]
								{selected.includes(tag.id)
								? 'bg-jade text-white'
								: 'bg-cream-dark text-ink-light'}
								{isSuggested(tag) ? 'border border-dashed border-white/70' : ''}"
						>
							{tagLabel(tag)}
							{#if isSuggested(tag)}
								<span class="ml-1 text-[10px] uppercase tracking-wide opacity-80">
									{t('pin.suggested')}
								</span>
							{/if}
						</button>
					{/if}
				{/each}
			</div>
		</div>
	{/each}
</div>
