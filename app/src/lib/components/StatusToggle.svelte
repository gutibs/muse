<script lang="ts">
	import type { PinStatus } from '$lib/types';
	import { t } from '$lib/i18n/index.svelte';

	let { value = $bindable('to_visit') }: { value: PinStatus } = $props();
</script>

<div class="flex gap-2">
	<button
		type="button"
		class="flex-1 rounded-chip px-4 py-2.5 text-sm font-medium transition-colors active:scale-[0.98] {value === 'to_visit' ? 'bg-jade text-white' : 'bg-cream-dark text-ink-muted'}"
		onclick={() => (value = 'to_visit')}
	>
		{t('common.toVisit')}
	</button>
	<button
		type="button"
		class="flex-1 rounded-chip px-4 py-2.5 text-sm font-medium transition-colors active:scale-[0.98] {value === 'visited' ? 'bg-jade text-white' : 'bg-cream-dark text-ink-muted'}"
		onclick={() => (value = 'visited')}
	>
		{t('common.visited')}
	</button>
</div>
