<script lang="ts">
	import { page } from '$app/state';
	import { untrack } from 'svelte';
	import Avatar from '$lib/components/Avatar.svelte';
	import DietaryBadges from '$lib/components/DietaryBadges.svelte';
	import { t } from '$lib/i18n/index.svelte';
	import { pinsService } from '$lib/services/pins.service';
	import { restaurantsService } from '$lib/services/restaurants.service';
	import type { Pin, RestaurantDetail } from '$lib/types';
	import { timeAgo } from '$lib/utils/time';

	let restaurantId = $derived(Number(page.params.id));

	let restaurant = $state<RestaurantDetail | null>(null);
	let myPin = $state<Pin | null>(null);
	let loading = $state(true);
	let error = $state('');

	$effect(() => {
		const id = restaurantId;
		if (!id) return;
		untrack(async () => {
			loading = true;
			error = '';
			try {
				restaurant = await restaurantsService.get(id);
				// Look up the current user's pin for this restaurant (if any) so we
				// can show an Edit / Add Pin button. The pins list endpoint
				// already filters to the current user.
				const res = await pinsService.list();
				myPin = res.results.find((p) => p.restaurant === id) ?? null;
			} catch {
				error = t('restaurant.cantLoad');
			} finally {
				loading = false;
			}
		});
	});

</script>

<div class="flex h-full flex-col">
	{#if loading}
		<div class="flex flex-1 items-center justify-center">
			<div class="h-7 w-7 animate-spin rounded-full border-2 border-jade border-t-transparent"></div>
		</div>
	{:else if error}
		<div class="flex flex-1 flex-col items-center justify-center px-6 text-center">
			<p class="text-sm text-blush">{error}</p>
		</div>
	{:else if restaurant}
		<!-- Hero image -->
		{#if restaurant.imageUrl}
			<div class="relative shrink-0">
				<img src={restaurant.imageUrl} alt={restaurant.name} class="h-48 w-full object-cover" />
				<div class="absolute inset-0 bg-gradient-to-t from-black/60 to-transparent"></div>
				<button onclick={() => history.back()} class="absolute left-4 top-4 flex h-9 w-9 items-center justify-center rounded-full bg-black/30 text-white active:scale-95" aria-label={t('common.back')}>
					<svg class="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="15 18 9 12 15 6"/></svg>
				</button>
				<div class="absolute bottom-4 left-5 right-5">
					<h1 class="text-xl font-bold text-white drop-shadow">{restaurant.name}</h1>
					<p class="text-sm text-white/80">
						{#if restaurant.city}{restaurant.city}{/if}
						{#if restaurant.cuisineDetail} · {restaurant.cuisineDetail.name}{/if}
						{#if restaurant.priceLevel} · {'$'.repeat(restaurant.priceLevel)}{/if}
					</p>
				</div>
			</div>
		{:else}
			<header class="flex shrink-0 items-center gap-3 px-5 py-3">
				<button onclick={() => history.back()} class="flex min-h-11 min-w-11 items-center justify-center text-ink active:opacity-70" aria-label={t('common.back')}>
					<svg class="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="15 18 9 12 15 6"/></svg>
				</button>
				<h1 class="flex-1 text-lg font-semibold text-ink">{restaurant.name}</h1>
			</header>
		{/if}

		<div class="min-h-0 flex-1 overflow-y-auto">
			<!-- Info bar -->
			<div class="flex items-center gap-3 px-5 py-3">
				{#if restaurant.averageRating}
					<div class="flex items-center gap-1">
						<div class="flex text-rose-400">
							{#each Array(5) as _, i}
								{#if i < Math.round(restaurant.averageRating ?? 0)}
									<svg class="h-4 w-4" viewBox="0 0 24 24" fill="currentColor"><path d="M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z"/></svg>
								{:else}
									<svg class="h-4 w-4 text-cream-dark" viewBox="0 0 24 24" fill="currentColor"><path d="M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z"/></svg>
								{/if}
							{/each}
						</div>
						<span class="text-sm font-semibold text-ink">{restaurant.averageRating.toFixed(1)}</span>
						<span class="text-xs text-ink-muted">({(restaurant.pinCount === 1 ? t('restaurant.reviewsCount') : t('restaurant.reviewsCountPlural')).replace('{count}', String(restaurant.pinCount))})</span>
					</div>
				{/if}
				{#if restaurant.tagsDetail?.length}
					<DietaryBadges tags={restaurant.tagsDetail} />
				{/if}
			</div>

			<!-- My pin: edit or add -->
			<div class="px-5 pb-2">
				{#if myPin}
					<a
						href={`/pin/${myPin.id}/edit`}
						class="flex min-h-12 w-full items-center justify-center gap-2 rounded-button bg-jade text-base font-semibold text-white active:scale-[0.98]"
					>
						<svg class="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
							<path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
						</svg>
						{t('restaurant.editMyPin')}
					</a>
				{:else}
					<a
						href={`/pin/new?restaurantId=${restaurant.id}`}
						class="flex min-h-12 w-full items-center justify-center gap-2 rounded-button bg-jade text-base font-semibold text-white active:scale-[0.98]"
					>
						<svg class="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
							<line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/>
						</svg>
						{t('restaurant.addToMyPins')}
					</a>
				{/if}
			</div>

			<!-- Info section: website + address -->
			<div class="space-y-3 px-5 pb-4">
				{#if restaurant.website}
					<a
						href={restaurant.website}
						target="_blank"
						rel="noopener"
						class="flex items-center gap-3 rounded-card bg-white p-4 shadow-card active:scale-[0.98]"
					>
						<svg class="h-5 w-5 shrink-0 text-jade" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
							<circle cx="12" cy="12" r="10"/><line x1="2" y1="12" x2="22" y2="12"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/>
						</svg>
						<span class="flex-1 truncate text-sm text-ink">
							{restaurant.website.replace(/^https?:\/\/(www\.)?/, '').replace(/\/$/, '')}
						</span>
						<svg class="h-4 w-4 shrink-0 text-ink-muted" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
							<path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/>
						</svg>
					</a>
				{/if}
				{#if restaurant.address}
					<a
						href={`/map?focus=${restaurant.id}`}
						class="flex items-start gap-3 rounded-card bg-white p-4 shadow-card active:scale-[0.98]"
					>
						<svg class="mt-0.5 h-5 w-5 shrink-0 text-jade" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
							<path d="M12 13a3 3 0 1 0 0-6 3 3 0 0 0 0 6Z"/>
							<path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7Z"/>
						</svg>
						<span class="flex-1 text-sm text-ink">{restaurant.address}{#if restaurant.city}, {restaurant.city}{/if}</span>
						<svg class="mt-0.5 h-4 w-4 shrink-0 text-ink-muted" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
							<polyline points="9 18 15 12 9 6" />
						</svg>
					</a>
				{/if}
			</div>

			<!-- Friend stats -->
			<div class="px-5 pb-4">
				<h2 class="mb-2 text-xs font-semibold uppercase tracking-wide text-ink-muted">{t('restaurant.fromYourFriends')}</h2>
				{#if restaurant.friendStats.ratedCount === 0 && restaurant.friendStats.onListCount === 0}
					<div class="rounded-card bg-white p-4 text-center shadow-card">
						<p class="text-sm text-ink-muted">{t('restaurant.noFriendsVisited')}</p>
					</div>
				{:else}
					<div class="grid grid-cols-3 gap-2">
						<!-- Friends rating avg -->
						<div class="rounded-card bg-white p-3 text-center shadow-card">
							{#if restaurant.friendStats.ratingAvg !== null}
								<div class="flex items-center justify-center gap-1 text-rose-400">
									<svg class="h-4 w-4" viewBox="0 0 24 24" fill="currentColor"><path d="M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z"/></svg>
									<span class="text-base font-bold text-ink">{restaurant.friendStats.ratingAvg}</span>
								</div>
							{:else}
								<div class="text-base font-bold text-ink-muted">—</div>
							{/if}
							<div class="mt-0.5 text-[10px] text-ink-muted">{t('restaurant.friendsRating')}</div>
						</div>

						<!-- Rated count -->
						<div class="rounded-card bg-white p-3 text-center shadow-card">
							<div class="text-base font-bold text-jade">{restaurant.friendStats.ratedCount}</div>
							<div class="mt-0.5 text-[10px] text-ink-muted">{t('restaurant.friendsRated')}</div>
						</div>

						<!-- On the list count -->
						<div class="rounded-card bg-white p-3 text-center shadow-card">
							<div class="text-base font-bold text-jade">{restaurant.friendStats.onListCount}</div>
							<div class="mt-0.5 text-[10px] text-ink-muted">{t('restaurant.onTheList')}</div>
						</div>
					</div>
				{/if}
			</div>

			<!-- Reviews header -->
			<div class="mx-5 rounded-card bg-cream-dark p-1">
				<div class="rounded-button bg-white py-2 text-center text-sm font-medium text-ink shadow-card">
					{t('restaurant.friendsNotes')}{restaurant.reviews?.length ? ` (${restaurant.reviews.length})` : ''}
				</div>
			</div>

			<!-- Reviews -->
			<div class="px-5 pb-6 pt-4">
				{#if !restaurant.reviews?.length}
					<p class="py-8 text-center text-sm text-ink-muted">{t('restaurant.notRatedYet')}</p>
				{:else}
					<ul class="space-y-3">
						{#each restaurant.reviews as review (review.id)}
							<li class="rounded-card bg-white p-4 shadow-card {review.isFriend ? 'ring-1 ring-jade/30' : ''}">
								<div class="flex items-start gap-3">
									<a href={`/users/${review.user.id}`} class="shrink-0">
										<Avatar name={review.user.displayName} src={review.user.avatar} size={36} />
									</a>
									<div class="min-w-0 flex-1">
										<div class="flex items-center justify-between">
											<div class="flex items-center gap-1.5">
												<a href={`/users/${review.user.id}`} class="text-sm font-semibold text-ink active:text-jade">
													{review.user.displayName || t('restaurant.anonymous')}
												</a>
												{#if review.isFriend}
													<span class="rounded-full bg-jade/10 px-1.5 py-0.5 text-[9px] font-medium uppercase text-jade">{t('restaurant.friendBadge')}</span>
												{/if}
											</div>
											<span class="text-xs text-ink-muted">{timeAgo(review.createdAt)}</span>
										</div>
										{#if review.rating}
											<div class="mt-0.5 flex gap-0.5 text-rose-400">
												{#each Array(5) as _, i}
													{#if i < review.rating}
														<svg class="h-3.5 w-3.5" viewBox="0 0 24 24" fill="currentColor"><path d="M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z"/></svg>
													{:else}
														<svg class="h-3.5 w-3.5 text-cream-dark" viewBox="0 0 24 24" fill="currentColor"><path d="M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z"/></svg>
													{/if}
												{/each}
											</div>
										{/if}
										<p class="mt-1.5 text-sm leading-relaxed text-ink-light">{review.comment}</p>
									</div>
								</div>
							</li>
						{/each}
					</ul>
				{/if}
			</div>
		</div>
	{/if}
</div>
