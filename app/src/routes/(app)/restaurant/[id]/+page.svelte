<script lang="ts">
	import { page } from '$app/state';
	import { untrack } from 'svelte';
	import Avatar from '$lib/components/Avatar.svelte';
	import DietaryBadges from '$lib/components/DietaryBadges.svelte';
	import { restaurantsService } from '$lib/services/restaurants.service';
	import type { MenuItem, RestaurantDetail } from '$lib/types';

	let restaurantId = $derived(Number(page.params.id));

	let restaurant = $state<RestaurantDetail | null>(null);
	let loading = $state(true);
	let error = $state('');
	let activeTab = $state<'menu' | 'reviews'>('menu');

	$effect(() => {
		const id = restaurantId;
		if (!id) return;
		untrack(async () => {
			loading = true;
			error = '';
			try {
				restaurant = await restaurantsService.get(id);
			} catch {
				error = 'Could not load restaurant.';
			} finally {
				loading = false;
			}
		});
	});

	const CATEGORY_ORDER = ['starter', 'main', 'side', 'dessert', 'drink'] as const;
	const CATEGORY_LABELS: Record<string, string> = {
		starter: 'Starters',
		main: 'Mains',
		side: 'Sides',
		dessert: 'Desserts',
		drink: 'Drinks',
	};

	let menuByCategory = $derived(() => {
		if (!restaurant?.menuItems) return [];
		const grouped = new Map<string, MenuItem[]>();
		for (const item of restaurant.menuItems) {
			const list = grouped.get(item.category) || [];
			list.push(item);
			grouped.set(item.category, list);
		}
		return CATEGORY_ORDER
			.filter((c) => grouped.has(c))
			.map((c) => ({ category: c, label: CATEGORY_LABELS[c], items: grouped.get(c)! }));
	});

	let recommended = $derived(
		restaurant?.menuItems?.filter((i) => i.isRecommended) ?? []
	);

	function formatPrice(rawPrice: number | string | null, currency: string): string {
		if (rawPrice === null || rawPrice === undefined) return '';
		const price = typeof rawPrice === 'string' ? parseFloat(rawPrice) : rawPrice;
		if (isNaN(price)) return '';
		const symbols: Record<string, string> = {
			USD: '$', GBP: '\u00a3', EUR: '\u20ac', ARS: 'AR$', JPY: '\u00a5',
			ILS: '\u20aa', ZAR: 'R', BRL: 'R$',
		};
		const sym = symbols[currency] || currency + ' ';
		if (currency === 'JPY') return `${sym}${price.toLocaleString()}`;
		return `${sym}${price.toFixed(price % 1 === 0 ? 0 : 2)}`;
	}

	function timeAgo(dateStr: string): string {
		const diff = Date.now() - new Date(dateStr).getTime();
		const days = Math.floor(diff / 86400000);
		if (days < 1) return 'today';
		if (days < 7) return `${days}d ago`;
		if (days < 30) return `${Math.floor(days / 7)}w ago`;
		return new Date(dateStr).toLocaleDateString('en-GB', { month: 'short', year: 'numeric' });
	}
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
				<a href="/search" class="absolute left-4 top-4 flex h-9 w-9 items-center justify-center rounded-full bg-black/30 text-white active:scale-95" aria-label="Back">
					<svg class="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="15 18 9 12 15 6"/></svg>
				</a>
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
				<a href="/search" class="flex min-h-11 min-w-11 items-center justify-center text-ink active:opacity-70" aria-label="Back">
					<svg class="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="15 18 9 12 15 6"/></svg>
				</a>
				<h1 class="flex-1 text-lg font-semibold text-ink">{restaurant.name}</h1>
			</header>
		{/if}

		<div class="min-h-0 flex-1 overflow-y-auto">
			<!-- Info bar -->
			<div class="flex items-center gap-3 px-5 py-3">
				{#if restaurant.averageRating}
					<div class="flex items-center gap-1">
						<div class="flex text-amber-400">
							{#each Array(5) as _, i}
								{#if i < Math.round(restaurant.averageRating ?? 0)}
									<svg class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor"><path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z"/></svg>
								{:else}
									<svg class="h-4 w-4 text-cream-dark" viewBox="0 0 20 20" fill="currentColor"><path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z"/></svg>
								{/if}
							{/each}
						</div>
						<span class="text-sm font-semibold text-ink">{restaurant.averageRating.toFixed(1)}</span>
						<span class="text-xs text-ink-muted">({restaurant.pinCount} review{restaurant.pinCount === 1 ? '' : 's'})</span>
					</div>
				{/if}
				{#if restaurant.tagsDetail?.length}
					<DietaryBadges tags={restaurant.tagsDetail} />
				{/if}
			</div>

			<!-- Recommended dishes -->
			{#if recommended.length > 0}
				<section class="px-5 pb-4">
					<h2 class="mb-2 text-sm font-semibold uppercase tracking-wide text-jade">Must Try</h2>
					<div class="flex gap-2 overflow-x-auto pb-1">
						{#each recommended as item (item.id)}
							<div class="flex shrink-0 items-center gap-2 rounded-card bg-jade/5 px-3 py-2">
								<span class="text-sm">🔥</span>
								<div>
									<p class="text-sm font-medium text-ink">{item.name}</p>
									{#if item.price !== null}
										<p class="text-xs text-jade">{formatPrice(item.price, item.currency)}</p>
									{/if}
								</div>
							</div>
						{/each}
					</div>
				</section>
			{/if}

			<!-- Tabs -->
			<div class="mx-5 flex gap-1 rounded-card bg-cream-dark p-1">
				<button
					onclick={() => (activeTab = 'menu')}
					class="flex-1 rounded-button py-2 text-sm font-medium active:scale-[0.98]
						{activeTab === 'menu' ? 'bg-white text-ink shadow-card' : 'text-ink-muted'}"
				>
					Menu{restaurant.menuItems?.length ? ` (${restaurant.menuItems.length})` : ''}
				</button>
				<button
					onclick={() => (activeTab = 'reviews')}
					class="flex-1 rounded-button py-2 text-sm font-medium active:scale-[0.98]
						{activeTab === 'reviews' ? 'bg-white text-ink shadow-card' : 'text-ink-muted'}"
				>
					Reviews{restaurant.reviews?.length ? ` (${restaurant.reviews.length})` : ''}
				</button>
			</div>

			<!-- Menu -->
			{#if activeTab === 'menu'}
				<div class="px-5 pb-6 pt-4">
					{#if menuByCategory().length === 0}
						<p class="py-8 text-center text-sm text-ink-muted">No menu available yet</p>
					{:else}
						{#each menuByCategory() as group}
							<div class="mb-5">
								<h3 class="mb-2 border-b border-cream-dark pb-1 text-xs font-semibold uppercase tracking-wider text-ink-muted">{group.label}</h3>
								<ul class="space-y-3">
									{#each group.items as item (item.id)}
										<li class="flex gap-3">
											<div class="min-w-0 flex-1">
												<div class="flex items-center gap-1.5">
													<p class="text-sm font-medium text-ink">{item.name}</p>
													{#if item.isRecommended}
														<span class="text-xs" title="Recommended">🔥</span>
													{/if}
													{#if item.isVegetarian}
														<span class="h-3.5 w-3.5 rounded-full bg-green-100 text-center text-[9px] leading-[14px] text-green-700" title="Vegetarian">V</span>
													{/if}
													{#if item.isGlutenFree}
														<span class="h-3.5 w-3.5 rounded-full bg-amber-100 text-center text-[9px] leading-[14px] text-amber-700" title="Gluten-free">GF</span>
													{/if}
												</div>
												{#if item.description}
													<p class="mt-0.5 text-xs leading-relaxed text-ink-muted">{item.description}</p>
												{/if}
											</div>
											{#if item.price !== null}
												<span class="shrink-0 text-sm font-semibold text-ink">{formatPrice(item.price, item.currency)}</span>
											{/if}
										</li>
									{/each}
								</ul>
							</div>
						{/each}
					{/if}
				</div>
			{/if}

			<!-- Reviews -->
			{#if activeTab === 'reviews'}
				<div class="px-5 pb-6 pt-4">
					{#if !restaurant.reviews?.length}
						<p class="py-8 text-center text-sm text-ink-muted">No reviews yet</p>
					{:else}
						<ul class="space-y-3">
							{#each restaurant.reviews as review (review.id)}
								<li class="rounded-card bg-white p-4 shadow-card">
									<div class="flex items-start gap-3">
										<a href={`/users/${review.user.id}`} class="shrink-0">
											<Avatar name={review.user.displayName} src={review.user.avatar} size={36} />
										</a>
										<div class="min-w-0 flex-1">
											<div class="flex items-center justify-between">
												<a href={`/users/${review.user.id}`} class="text-sm font-semibold text-ink active:text-jade">
													{review.user.displayName || 'Anonymous'}
												</a>
												<span class="text-xs text-ink-muted">{timeAgo(review.createdAt)}</span>
											</div>
											{#if review.rating}
												<div class="mt-0.5 flex text-amber-400">
													{#each Array(5) as _, i}
														{#if i < review.rating}
															<svg class="h-3.5 w-3.5" viewBox="0 0 20 20" fill="currentColor"><path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z"/></svg>
														{:else}
															<svg class="h-3.5 w-3.5 text-cream-dark" viewBox="0 0 20 20" fill="currentColor"><path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z"/></svg>
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
			{/if}
		</div>
	{/if}
</div>
