<script lang="ts">
	import { page } from '$app/state';
	import Avatar from '$lib/components/Avatar.svelte';
	import MuseLogo from '$lib/components/MuseLogo.svelte';
	import { t } from '$lib/i18n/index.svelte';
	import { feedService } from '$lib/services/feed.service';
	import { friendsService } from '$lib/services/friends.service';
	import { authStore } from '$lib/stores/auth.store.svelte';
	import type { Activity } from '$lib/types';
	import { timeAgo } from '$lib/utils/time';

	let pendingRestaurant = $derived(page.url.searchParams.get('pending'));

	const greeting = $derived.by(() => {
		const hour = new Date().getHours();
		if (hour < 12) return t('home.goodMorning');
		if (hour < 18) return t('home.goodAfternoon');
		return t('home.goodEvening');
	});

	let recentActivity = $state<Activity[]>([]);
	let pendingRequests = $state(0);
	let loadingActivity = $state(true);

	$effect(() => {
		if (!authStore.isAuthenticated) return;
		let cancelled = false;
		Promise.all([feedService.list(), friendsService.requests()])
			.then(([feed, reqs]) => {
				if (cancelled) return;
				recentActivity = feed.results.slice(0, 5);
				pendingRequests = reqs.length;
			})
			.catch((err) => {
				if (!cancelled) console.error('[home] load failed:', err);
			})
			.finally(() => {
				if (!cancelled) loadingActivity = false;
			});
		return () => { cancelled = true; };
	});

	function activityText(a: Activity): string {
		if (a.verb === 'joined') return t('feed.joinedMuse');
		if (a.verb === 'friendship' && a.targetUser) return `${t('feed.becameFriends')} ${a.targetUser.displayName || a.targetUser.email}`;
		if (a.verb === 'rated' && a.pin) return `${t('feed.visited')} ${a.pin.restaurantDetail.name}`;
		if (a.verb === 'pinned' && a.pin) return t('feed.wantsToVisit').replace('{restaurant}', a.pin.restaurantDetail.name);
		if (a.verb === 'updated' && a.pin) return `${t('feed.updated')} ${a.pin.restaurantDetail.name}`;
		return a.verb;
	}
</script>

<div class="flex h-full flex-col">
	<header class="shrink-0 px-5 pb-4 pt-6">
		<div class="flex items-center justify-between">
			<div class="flex items-center gap-3">
				<Avatar
					name={authStore.user?.displayName || ''}
					src={authStore.user?.avatar}
					size={48}
				/>
				<div>
					<p class="text-sm text-ink-muted">{greeting}</p>
					<h1 class="text-xl font-semibold text-ink">
						{authStore.user?.displayName || 'Welcome'}
					</h1>
				</div>
			</div>
			<MuseLogo width={80} />
		</div>
	</header>

	<div class="flex-1 space-y-6 overflow-y-auto px-5 pb-6">
		<!-- Stats -->
		{#if authStore.user?.stats}
			<div class="flex gap-3">
				<div class="flex-1 rounded-card bg-white p-4 shadow-card">
					<div class="text-2xl font-bold text-jade">{authStore.user.stats.pinCount}</div>
					<div class="text-xs text-ink-muted">{t('home.pins')}</div>
				</div>
				<div class="flex-1 rounded-card bg-white p-4 shadow-card">
					<div class="text-2xl font-bold text-jade">{authStore.user.stats.visitedCount}</div>
					<div class="text-xs text-ink-muted">{t('home.visited')}</div>
				</div>
				<div class="flex-1 rounded-card bg-white p-4 shadow-card">
					<div class="text-2xl font-bold text-jade">{authStore.user.stats.friendCount}</div>
					<div class="text-xs text-ink-muted">{t('home.friends')}</div>
				</div>
			</div>
		{/if}

		<!-- Restaurant submitted for approval -->
		{#if pendingRestaurant}
			<div class="flex items-start gap-3 rounded-card bg-amber-50 p-4 shadow-card">
				<div class="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-amber-100 text-amber-700">
					<svg class="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
						<circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>
					</svg>
				</div>
				<div class="min-w-0 flex-1">
					<div class="text-sm font-semibold text-amber-900">"{pendingRestaurant}" submitted</div>
					<div class="text-xs text-amber-800">It will appear once approved by an admin.</div>
				</div>
			</div>
		{/if}

		<!-- Pending friend requests -->
		{#if pendingRequests > 0}
			<a
				href="/friends"
				class="flex items-center gap-3 rounded-card bg-jade/10 p-4 shadow-card active:scale-[0.98]"
			>
				<div class="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-jade text-white">
					<span class="text-sm font-bold">{pendingRequests}</span>
				</div>
				<div class="min-w-0 flex-1">
					<div class="text-sm font-semibold text-jade">{pendingRequests > 1 ? t('home.friendRequestsPlural') : t('home.friendRequests')}</div>
					<div class="text-xs text-jade/70">{t('home.tapToView')}</div>
				</div>
				<svg class="h-4 w-4 text-jade" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
					<polyline points="9 18 15 12 9 6" />
				</svg>
			</a>
		{/if}

		<!-- Primary action -->
		<a
			href="/pin/new"
			class="flex items-center gap-4 rounded-card bg-jade p-4 shadow-card active:scale-[0.98]"
		>
			<div class="flex h-12 w-12 shrink-0 items-center justify-center rounded-full bg-white/20">
				<svg class="h-6 w-6 text-white" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
					<line x1="12" y1="5" x2="12" y2="19" />
					<line x1="5" y1="12" x2="19" y2="12" />
				</svg>
			</div>
			<div class="flex-1">
				<div class="text-base font-semibold text-white">{t('home.addPin')}</div>
				<div class="text-xs text-white/70">{t('home.addPinDesc')}</div>
			</div>
			<svg class="h-5 w-5 shrink-0 text-white/50" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
				<polyline points="9 18 15 12 9 6" />
			</svg>
		</a>

		<!-- Secondary actions -->
		<div class="flex gap-2">
			<a href="/map" class="flex flex-1 items-center gap-2.5 rounded-card bg-white px-4 py-3 shadow-card active:scale-[0.98]">
				<svg class="h-5 w-5 shrink-0 text-jade" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
					<path d="M12 13a3 3 0 1 0 0-6 3 3 0 0 0 0 6Z" /><path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7Z" />
				</svg>
				<span class="text-sm font-medium text-ink">{t('home.explore')}</span>
			</a>
			<a href="/search" class="flex flex-1 items-center gap-2.5 rounded-card bg-white px-4 py-3 shadow-card active:scale-[0.98]">
				<svg class="h-5 w-5 shrink-0 text-jade" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
					<circle cx="11" cy="11" r="8" /><path d="m21 21-4.3-4.3" />
				</svg>
				<span class="text-sm font-medium text-ink">{t('nav.search')}</span>
			</a>
			<a href="/friends" class="flex flex-1 items-center gap-2.5 rounded-card bg-white px-4 py-3 shadow-card active:scale-[0.98]">
				<svg class="h-5 w-5 shrink-0 text-jade" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
					<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" /><circle cx="9" cy="7" r="4" />
				</svg>
				<span class="text-sm font-medium text-ink">{t('home.friends')}</span>
			</a>
		</div>

		<!-- Recent Activity (real) -->
		<section>
			<div class="mb-3 flex items-center justify-between">
				<h2 class="text-sm font-semibold uppercase tracking-wide text-ink-muted">{t('home.recentActivity')}</h2>
				{#if recentActivity.length > 0}
					<a href="/feed" class="text-xs font-medium text-jade active:opacity-70">{t('home.seeAll')}</a>
				{/if}
			</div>

			{#if loadingActivity}
				<div class="space-y-2">
					{#each Array(3) as _}
						<div class="animate-pulse rounded-card bg-white p-4 shadow-card">
							<div class="flex gap-3">
								<div class="h-8 w-8 rounded-full bg-cream-dark"></div>
								<div class="flex-1 space-y-2">
									<div class="h-3 w-3/4 rounded bg-cream-dark"></div>
									<div class="h-3 w-1/2 rounded bg-cream-dark"></div>
								</div>
							</div>
						</div>
					{/each}
				</div>
			{:else if recentActivity.length === 0}
				<div class="rounded-card bg-white p-5 shadow-card">
					<p class="text-center text-sm text-ink-muted">
						{t('home.noActivity')}
					</p>
				</div>
			{:else}
				<div class="space-y-2">
					{#each recentActivity as activity (activity.id)}
						<div class="flex items-start gap-3 rounded-card bg-white p-4 shadow-card">
							<Avatar name={activity.actor.displayName} src={activity.actor.avatar} size={32} />
							<div class="min-w-0 flex-1">
								<p class="text-sm text-ink">
									<span class="font-semibold">{activity.actor.displayName || activity.actor.email}</span>
									{' '}
									<span class="text-ink-muted">{activityText(activity)}</span>
								</p>
								{#if activity.pin?.rating}
									<div class="mt-0.5 flex text-rose-400">
										{#each Array(5) as _, i}
											{#if i < activity.pin.rating}
												<svg class="h-3 w-3" viewBox="0 0 24 24" fill="currentColor"><path d="M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z"/></svg>
											{:else}
												<svg class="h-3 w-3 text-cream-dark" viewBox="0 0 24 24" fill="currentColor"><path d="M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z"/></svg>
											{/if}
										{/each}
									</div>
								{/if}
								<p class="mt-0.5 text-xs text-ink-muted">{timeAgo(activity.createdAt)}</p>
							</div>
						</div>
					{/each}
				</div>
			{/if}
		</section>
	</div>
</div>
