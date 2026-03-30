<script lang="ts">
	import type { Snippet } from 'svelte';

	let { children }: { children: Snippet } = $props();
</script>

<div
	class="flex h-full w-full flex-col"
	style="
		padding-top: var(--sat);
		padding-bottom: var(--sab);
		padding-left: var(--sal);
		padding-right: var(--sar);
	"
>
	{@render children()}
</div>
