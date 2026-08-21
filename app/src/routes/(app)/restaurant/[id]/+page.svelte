<script lang="ts">
	import { page } from '$app/state';
	import { untrack } from 'svelte';
	import Avatar from '$lib/components/Avatar.svelte';
	import DietaryBadges from '$lib/components/DietaryBadges.svelte';
	import { t } from '$lib/i18n/index.svelte';
	import {
		trackExternalActionClick,
		trackVenueDetailView,
	} from '$lib/services/analytics.service';
	import { pinsService } from '$lib/services/pins.service';
	import { restaurantsService } from '$lib/services/restaurants.service';
	import type { Pin, RestaurantDetail } from '$lib/types';
	import { timeAgo } from '$lib/utils/time';
	import { logSilent } from '$lib/utils/logger';
	import { directionsUrl, openExternal } from '$lib/utils/external';
	import RatingHearts from '$lib/components/RatingHearts.svelte';
	import HeartIcon from '$lib/components/HeartIcon.svelte';

	let restaurantId = $derived(Number(page.params.id));

	let restaurant = $state<RestaurantDetail | null>(null);
	let myPin = $state<Pin | null>(null);
	let loading = $state(true);
	let error = $state('');

	// Google puede mandar más de un autor; se muestra el primero, que es el de
	// la foto que efectivamente servimos (el parser toma photos[0]).
	let photoAuthor = $derived(restaurant?.photoAttribution?.[0] ?? null);

	function goToDirections() {
		if (!restaurant) return;
		trackExternalActionClick(restaurant.id, 'directions', { surface: 'restaurant' });
		openExternal(directionsUrl(restaurant.lat, restaurant.lng));
	}

	function goToReservation() {
		if (!restaurant?.reservation) return;
		trackExternalActionClick(restaurant.id, 'reservation', {
			surface: 'restaurant',
			provider: restaurant.reservation.provider,
		});
		openExternal(restaurant.reservation.url);
	}

	function goToWebsite() {
		if (!restaurant?.website) return;
		trackExternalActionClick(restaurant.id, 'website', { surface: 'restaurant' });
		openExternal(restaurant.website);
	}

	$effect(() => {
		const id = restaurantId;
		if (!id) return;
		untrack(async () => {
			loading = true;
			error = '';
			try {
				restaurant = await restaurantsService.get(id);
				// Después del fetch y no antes: si la ficha no cargó, nadie la vio.
				trackVenueDetailView(id);
				// Look up the current user's pin for this restaurant (if any) so we
				// can show an Edit / Add Pin button. The pins list endpoint
				// already filters to the current user.
				//
				// listAll rather than list: searching only the first page meant
				// that with 21+ pins an already-pinned restaurant offered "add
				// pin", and tapping it got a 409 from the backend.
				const pins = await pinsService.listAll();
				myPin = pins.find((p) => p.restaurant === id) ?? null;
			} catch (err) {
				error = t('restaurant.cantLoad');
				logSilent('restaurant:load', err);
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
				{#if photoAuthor}
					<!-- Crédito del autor de la foto: los Google Maps Platform Terms
					     exigen mostrarlo junto a la foto que servimos desde nuestro
					     propio storage. Arriba a la derecha para no chocar con el
					     nombre del restaurante, que va abajo. -->
					<a
						href={photoAuthor.uri}
						target="_blank"
						rel="noopener noreferrer"
						class="absolute right-4 top-4 rounded-full bg-black/30 px-2 py-1 text-[11px] text-white/90 active:opacity-70"
					>
						{t('restaurant.photoBy').replace('{author}', photoAuthor.displayName)}
					</a>
				{/if}
				<div class="absolute bottom-4 left-5 right-5">
					<h1 class="text-xl font-bold text-white drop-shadow">{restaurant.name}</h1>
					<p class="text-sm text-white/80">
						{#if restaurant.city}{restaurant.city}{/if}
						{#if restaurant.cuisinesDetail?.length} · {restaurant.cuisinesDetail.map((c) => c.name).join(' · ')}{/if}
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
						<RatingHearts value={restaurant.averageRating} size="lg" />
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

			{#if restaurant.isClosed}
				<!-- Un lugar cerrado conserva su ficha porque hay pins que apuntan
				     acá, pero no se lo manda a nadie: ni indicaciones ni reserva. -->
				<div class="mx-5 mb-4 rounded-card border border-blush/40 bg-blush/5 p-4">
					<p class="text-sm font-semibold text-blush">{t('restaurant.closed')}</p>
					<p class="mt-1 text-xs text-ink-light">{t('restaurant.closedNote')}</p>
				</div>
			{/if}

			<!-- Salidas externas. Son los únicos botones que sacan al usuario de
			     la app, y los tres reportan el mismo evento con distinto destino. -->
			{#if !restaurant.isClosed}
			<div class="flex gap-2 px-5 pb-4">
				<button
					type="button"
					onclick={goToDirections}
					class="flex min-h-11 flex-1 items-center justify-center gap-2 rounded-card bg-jade px-3 py-3 text-sm font-semibold text-white shadow-card active:scale-[0.98]"
				>
					<svg class="h-4 w-4 shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
						<polygon points="3 11 22 2 13 21 11 13 3 11"/>
					</svg>
					{t('restaurant.directions')}
				</button>
				{#if restaurant.reservation}
					<button
						type="button"
						onclick={goToReservation}
						class="flex min-h-11 flex-1 items-center justify-center gap-2 rounded-card bg-white px-3 py-3 text-sm font-semibold text-ink shadow-card active:scale-[0.98]"
					>
						<svg class="h-4 w-4 shrink-0 text-jade" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
							<rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/>
						</svg>
						{t('restaurant.book')}
					</button>
				{/if}
			</div>
			{/if}

			<!-- Info section: website + address -->
			<div class="space-y-3 px-5 pb-4">
				{#if restaurant.website}
					<button
						type="button"
						onclick={goToWebsite}
						class="flex w-full items-center gap-3 rounded-card bg-white p-4 text-left shadow-card active:scale-[0.98]"
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
					</button>
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
									<HeartIcon />
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
									<!-- An erased author keeps the review but loses the byline: no
									     avatar, no name, and no link (their profile is gone). -->
									{#if review.user.isDeleted}
										<div class="shrink-0">
											<Avatar name={t('restaurant.anonymous')} src={null} size={36} />
										</div>
									{:else}
										<a href={`/users/${review.user.id}`} class="shrink-0">
											<Avatar name={review.user.displayName} src={review.user.avatar} size={36} />
										</a>
									{/if}
									<div class="min-w-0 flex-1">
										<div class="flex items-center justify-between">
											<div class="flex items-center gap-1.5">
												{#if review.user.isDeleted}
													<span class="text-sm font-semibold text-ink-muted">{t('restaurant.anonymous')}</span>
												{:else}
													<a href={`/users/${review.user.id}`} class="text-sm font-semibold text-ink active:text-jade">
														{review.user.displayName || t('restaurant.anonymous')}
													</a>
												{/if}
												{#if review.isFriend}
													<span class="rounded-full bg-jade/10 px-1.5 py-0.5 text-[9px] font-medium uppercase text-jade">{t('restaurant.friendBadge')}</span>
												{/if}
											</div>
											<span class="text-xs text-ink-muted">{timeAgo(review.createdAt)}</span>
										</div>
										{#if review.rating}
											<RatingHearts value={review.rating} class="mt-0.5  gap-0.5" />
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
