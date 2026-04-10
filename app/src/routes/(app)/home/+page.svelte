<script lang="ts">
	import Avatar from '$lib/components/Avatar.svelte';
	import MuseLogo from '$lib/components/MuseLogo.svelte';
	import { authStore } from '$lib/stores/auth.store.svelte';

	const greeting = $derived(() => {
		const hour = new Date().getHours();
		if (hour < 12) return 'Good morning';
		if (hour < 18) return 'Good afternoon';
		return 'Good evening';
	});

	interface QuickAction {
		label: string;
		description: string;
		href: string;
		icon: string;
	}

	const actions: QuickAction[] = [
		{
			label: 'Add a Pin',
			description: 'Tag a restaurant you visited or want to visit',
			href: '/map',
			icon: 'pin',
		},
		{
			label: 'Find Friends',
			description: 'Invite friends and see their recommendations',
			href: '/friends',
			icon: 'friends',
		},
		{
			label: 'Explore Map',
			description: 'Discover restaurants on the map',
			href: '/map',
			icon: 'map',
		},
		{
			label: 'Search',
			description: 'Find restaurants, cuisines, or people',
			href: '/search',
			icon: 'search',
		},
	];
</script>

<div class="flex h-full flex-col">
	<!-- Header -->
	<header class="shrink-0 px-5 pb-4 pt-6">
		<div class="flex items-center justify-between">
			<div class="flex items-center gap-3">
				<Avatar
					name={authStore.user?.displayName || ''}
					src={authStore.user?.avatar}
					size={48}
				/>
				<div>
					<p class="text-sm text-ink-muted">{greeting()}</p>
					<h1 class="text-xl font-semibold text-ink"> acaaaaaa
						{authStore.user?.displayName || 'Welcome'}
					</h1>
				</div>
			</div>
			<MuseLogo width={48} />
		</div>
	</header>

	<!-- Content -->
	<div class="flex-1 space-y-6 overflow-y-auto px-5 pb-6">
		<!-- Stats -->
		{#if authStore.user?.stats}
			<div class="flex gap-3">
				<div class="flex-1 rounded-card bg-white p-4 shadow-card">
					<div class="text-2xl font-bold text-jade">{authStore.user.stats.pinCount}</div>
					<div class="text-xs text-ink-muted">Pins</div>
				</div>
				<div class="flex-1 rounded-card bg-white p-4 shadow-card">
					<div class="text-2xl font-bold text-jade">{authStore.user.stats.visitedCount}</div>
					<div class="text-xs text-ink-muted">Visited</div>
				</div>
				<div class="flex-1 rounded-card bg-white p-4 shadow-card">
					<div class="text-2xl font-bold text-jade">{authStore.user.stats.friendCount}</div>
					<div class="text-xs text-ink-muted">Friends</div>
				</div>
			</div>
		{/if}

		<!-- Quick Actions -->
		<section>
			<h2 class="mb-3 text-sm font-semibold uppercase tracking-wide text-ink-muted">Quick Actions</h2>
			<div class="space-y-2">
				{#each actions as action}
					<a
						href={action.href}
						class="flex items-center gap-4 rounded-card bg-white p-4 shadow-card transition-transform active:scale-[0.98]"
					>
						<div class="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-jade/10 text-jade">
							{#if action.icon === 'pin'}
								<svg class="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
									<path d="M12 13a3 3 0 1 0 0-6 3 3 0 0 0 0 6Z" />
									<path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7Z" />
								</svg>
							{:else if action.icon === 'friends'}
								<svg class="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
									<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" />
									<circle cx="9" cy="7" r="4" />
									<path d="M22 21v-2a4 4 0 0 0-3-3.87" />
									<path d="M16 3.13a4 4 0 0 1 0 7.75" />
								</svg>
							{:else if action.icon === 'map'}
								<svg class="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
									<polygon points="1 6 1 22 8 18 16 22 23 18 23 2 16 6 8 2 1 6" />
									<line x1="8" y1="2" x2="8" y2="18" />
									<line x1="16" y1="6" x2="16" y2="22" />
								</svg>
							{:else if action.icon === 'search'}
								<svg class="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
									<circle cx="11" cy="11" r="8" />
									<path d="m21 21-4.3-4.3" />
								</svg>
							{/if}
						</div>
						<div class="min-w-0 flex-1">
							<div class="text-sm font-semibold text-ink">{action.label}</div>
							<div class="text-xs text-ink-muted">{action.description}</div>
						</div>
						<svg class="h-4 w-4 shrink-0 text-ink-muted" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
							<polyline points="9 18 15 12 9 6" />
						</svg>
					</a>
				{/each}
			</div>
		</section>

		<!-- Activity Preview -->
		<section>
			<h2 class="mb-3 text-sm font-semibold uppercase tracking-wide text-ink-muted">Recent Activity</h2>
			<div class="rounded-card bg-white p-5 shadow-card">
				<p class="text-center text-sm text-ink-muted">
					No activity yet. Add friends to see where they've been eating.
				</p>
			</div>
		</section>
	</div>
</div>
