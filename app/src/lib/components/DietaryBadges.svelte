<script lang="ts">
	import type { Tag } from '$lib/types';

	let { tags = [] }: { tags?: Tag[] } = $props();

	const BADGE_MAP: Record<string, { label: string; icon: string; bg: string; text: string }> = {
		'kosher': { label: 'Kosher', icon: '✡', bg: 'bg-blue-50', text: 'text-blue-700' },
		'sin-tacc': { label: 'Sin TACC', icon: '🌾', bg: 'bg-amber-50', text: 'text-amber-700' },
	};

	let badges = $derived(
		tags
			.filter((t) => BADGE_MAP[t.slug])
			.map((t) => ({ ...BADGE_MAP[t.slug], slug: t.slug }))
	);
</script>

{#if badges.length > 0}
	<div class="flex flex-wrap gap-1">
		{#each badges as badge (badge.slug)}
			<span class="inline-flex items-center gap-0.5 rounded-full px-2 py-0.5 text-xs font-medium {badge.bg} {badge.text}">
				<span class="text-[10px]">{badge.icon}</span>
				{badge.label}
			</span>
		{/each}
	</div>
{/if}
