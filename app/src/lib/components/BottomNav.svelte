<script lang="ts">
	import { page } from '$app/state';
	import { t } from '$lib/i18n/index.svelte';

	const tabs = [
		{ path: '/home', key: 'nav.home', icon: 'home' },
		{ path: '/feed', key: 'nav.feed', icon: 'feed' },
		{ path: '/map', key: 'nav.map', icon: 'map' },
		{ path: '/search', key: 'nav.search', icon: 'search' },
		{ path: '/profile', key: 'nav.profile', icon: 'profile' },
	] as const;

	function isActive(tabPath: string): boolean {
		return page.url.pathname.startsWith(tabPath);
	}
</script>

<nav class="shrink-0 border-t border-cream-dark bg-white">
	<div class="flex justify-around px-1 py-1">
		{#each tabs as tab}
			<a
				href={tab.path}
				class="flex min-h-11 min-w-11 flex-col items-center justify-center gap-0.5 rounded-lg px-2 py-1 text-xs transition-colors active:scale-95 {isActive(tab.path) ? 'text-jade font-medium' : 'text-ink-muted'}"
			>
				{#if tab.icon === 'home'}
					<svg class="h-6 w-6" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
						<path d="m3 9 9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" />
						<polyline points="9 22 9 12 15 12 15 22" />
					</svg>
				{:else if tab.icon === 'feed'}
					<svg class="h-6 w-6" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
						<path d="M3 2v7c0 1.1.9 2 2 2h4a2 2 0 0 0 2-2V2"/><path d="M7 2v20"/><path d="M21 15V2v0a5 5 0 0 0-5 5v6c0 1.1.9 2 2 2h3Zm0 0v7"/>
					</svg>
				{:else if tab.icon === 'map'}
					<svg class="h-6 w-6" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
						<path d="M12 13a3 3 0 1 0 0-6 3 3 0 0 0 0 6Z" />
						<path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7Z" />
					</svg>
				{:else if tab.icon === 'search'}
					<svg class="h-6 w-6" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
						<circle cx="11" cy="11" r="8" />
						<path d="m21 21-4.3-4.3" />
					</svg>
				{:else if tab.icon === 'profile'}
					<svg class="h-6 w-6" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
						<path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
						<circle cx="12" cy="7" r="4" />
					</svg>
				{/if}
				<span>{t(tab.key)}</span>
			</a>
		{/each}
	</div>
</nav>
