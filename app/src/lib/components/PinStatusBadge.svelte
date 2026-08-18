<script lang="ts">
	import type { PinStatus } from '$lib/types';

	let {
		status,
		label,
	}: {
		status: PinStatus;
		/** Each screen words it differently ("Visited" vs "Rated"), so it comes in. */
		label: string;
	} = $props();
</script>

<span
	class="shrink-0 rounded-full px-2 py-0.5 text-xs font-medium {status === 'visited'
		? 'bg-jade/10 text-jade'
		: 'bg-cream-dark text-ink-muted'}"
>
	{label}
</span>
