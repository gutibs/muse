<script lang="ts">
	import Avatar from '$lib/components/Avatar.svelte';
	import { feedService } from '$lib/services/feed.service';
	import { t } from '$lib/i18n/index.svelte';
	import type { Activity } from '$lib/types';

	let activities = $state<Activity[]>([]);
	let loading = $state(true);
	let loadingMore = $state(false);
	let nextPage = $state<number | null>(null);
	let error = $state('');

	async function load(page = 1) {
		if (page === 1) loading = true;
		else loadingMore = true;
		error = '';
		try {
			const res = await feedService.list(page);
			if (page === 1) activities = res.results;
			else activities = [...activities, ...res.results];
			nextPage = res.next ? page + 1 : null;
		} catch {
			error = 'Could not load feed.';
		} finally {
			loading = false;
			loadingMore = false;
		}
	}

	$effect(() => { load(1); });

	function timeAgo(dateStr: string): string {
		const diff = Date.now() - new Date(dateStr).getTime();
		const mins = Math.floor(diff / 60000);
		if (mins < 1) return 'just now';
		if (mins < 60) return `${mins}m ago`;
		const hours = Math.floor(mins / 60);
		if (hours < 24) return `${hours}h ago`;
		const days = Math.floor(hours / 24);
		if (days < 7) return `${days}d ago`;
		return new Date(dateStr).toLocaleDateString('en-GB', { day: 'numeric', month: 'short' });
	}

	function verbLabel(a: Activity): string {
		switch (a.verb) {
			case 'pinned': return t('feed.wantsToVisit');
			case 'rated': return t('feed.visited');
			case 'updated': return t('feed.updated');
			case 'friendship': return t('feed.becameFriends');
			case 'joined': return t('feed.joinedMuse');
		}
	}

	function stars(n: number): string {
		return '★'.repeat(n) + '☆'.repeat(5 - n);
	}
</script>

<div class="flex h-full flex-col">
	<header class="shrink-0 px-5 py-4">
		<h1 class="text-lg font-semibold text-ink">{t('feed.title')}</h1>
		<p class="text-xs text-ink-muted">{t('feed.subtitle')}</p>
	</header>

	<main class="flex-1 overflow-y-auto px-5 pb-6">
		{#if loading}
			<div class="flex justify-center py-16">
				<div class="h-7 w-7 animate-spin rounded-full border-2 border-jade border-t-transparent"></div>
			</div>

		{:else if error}
			<div class="flex flex-col items-center py-16 text-center">
				<p class="text-sm text-blush">{error}</p>
				<button onclick={() => load(1)} class="mt-3 text-sm font-medium text-jade active:opacity-70">
					{t('feed.tryAgain')}
				</button>
			</div>

		{:else if activities.length === 0}
			<div class="flex flex-col items-center py-16 text-center">
				<div class="mb-3 flex h-14 w-14 items-center justify-center rounded-full bg-jade/10 text-jade">
					<svg class="h-7 w-7" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
						<path d="M22 12h-4l-3 9L9 3l-3 9H2" />
					</svg>
				</div>
				<p class="text-sm font-medium text-ink">{t('feed.empty')}</p>
				<p class="mt-1 text-xs text-ink-muted">{t('feed.emptyDesc')}</p>
				<a
					href="/friends"
					class="mt-4 rounded-button bg-jade px-5 py-2.5 text-sm font-semibold text-white active:scale-[0.98]"
				>
					{t('feed.findFriends')}
				</a>
			</div>

		{:else}
			<ul class="space-y-3">
				{#each activities as activity (activity.id)}
					<li class="rounded-card bg-white p-4 shadow-card">
						<div class="flex items-start gap-3">
							<a href={`/users/${activity.actor.id}`} class="shrink-0">
								<Avatar
									name={activity.actor.displayName}
									src={activity.actor.avatar}
									size={40}
								/>
							</a>
							<div class="min-w-0 flex-1">
								<!-- Main line -->
								<p class="text-sm text-ink">
									<a href={`/users/${activity.actor.id}`} class="font-semibold text-ink active:text-jade">{activity.actor.displayName || activity.actor.email}</a>
									{' '}
									{#if activity.verb === 'joined'}
										<span class="text-ink-muted">{t('feed.joinedMuse')} 🎉</span>
									{:else if activity.verb === 'friendship' && activity.targetUser}
										<span class="text-ink-muted">{t('feed.becameFriends')}</span>
										{' '}
										<span class="font-semibold">{activity.targetUser.displayName || activity.targetUser.email}</span>
									{:else if activity.pin}
										<span class="text-ink-muted">{verbLabel(activity)}</span>
										{' '}
										<span class="font-semibold">{activity.pin.restaurantDetail.name}</span>
										{#if activity.pin.restaurantDetail.city}
											<span class="text-ink-muted">, {activity.pin.restaurantDetail.city}</span>
										{/if}
									{/if}
								</p>

								<!-- Rating -->
								{#if activity.verb === 'rated' && activity.pin?.rating}
									<p class="mt-0.5 text-sm tracking-tight text-amber-500">
										{stars(activity.pin.rating)}
									</p>
								{/if}

								<!-- Comment -->
								{#if activity.pin?.comment}
									<p class="mt-1 text-xs italic text-ink-muted">"{activity.pin.comment}"</p>
								{/if}

								<!-- Personas -->
								{#if activity.pin?.personasDetail?.length}
									<div class="mt-1.5 flex flex-wrap gap-1">
										{#each activity.pin.personasDetail as persona}
											<span class="rounded-full bg-cream-dark px-2 py-0.5 text-xs text-ink-muted">
												{persona.icon} {persona.name}
											</span>
										{/each}
									</div>
								{/if}

								<!-- Timestamp -->
								<p class="mt-1.5 text-xs text-ink-muted">{timeAgo(activity.createdAt)}</p>
							</div>
						</div>
					</li>
				{/each}
			</ul>

			{#if nextPage}
				<div class="mt-4 flex justify-center">
					<button
						onclick={() => load(nextPage!)}
						disabled={loadingMore}
						class="flex min-h-11 items-center gap-2 rounded-button border border-cream-dark px-5 text-sm font-medium text-ink-muted active:scale-[0.98] disabled:opacity-50"
					>
						{#if loadingMore}
							<div class="h-4 w-4 animate-spin rounded-full border-2 border-jade border-t-transparent"></div>
						{:else}
							{t('feed.loadMore')}
						{/if}
					</button>
				</div>
			{/if}
		{/if}
	</main>
</div>
