<script lang="ts">
	import type { Persona } from '$lib/types';

	let {
		personas = [],
		selected = $bindable([]),
	}: {
		personas: Persona[];
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

<div class="flex flex-wrap gap-2">
	{#each personas as persona}
		<button
			type="button"
			class="flex items-center gap-1.5 rounded-chip px-3 py-2 text-sm transition-colors active:scale-[0.98] {selected.includes(persona.id) ? 'bg-jade text-white' : 'bg-cream-dark text-ink-light'}"
			onclick={() => toggle(persona.id)}
		>
			<span>{persona.icon}</span>
			<span>{persona.name}</span>
		</button>
	{/each}
</div>
