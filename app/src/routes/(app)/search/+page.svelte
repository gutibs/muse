<script lang="ts">
	import { browser } from '$app/environment';
	import { goto } from '$app/navigation';
	import DietaryBadges from '$lib/components/DietaryBadges.svelte';
	import MapView from '$lib/components/MapView.svelte';
	import { t } from '$lib/i18n/index.svelte';
	import { restaurantsService } from '$lib/services/restaurants.service';
	import type { Cuisine, Restaurant } from '$lib/types';
	import { dietaryBadgesHtml } from '$lib/utils/dietary-badges';
	import type L from 'leaflet';

	function viewRestaurant(r: Restaurant) {
		goto(`/restaurant/${r.id}`);
	}

	let query = $state('');
	let cityFilter = $state('');
	let cuisineFilter = $state('');

	let cuisines = $state<Cuisine[]>([]);
	let results = $state<Restaurant[]>([]);
	let view = $state<'list' | 'map'>('list');

	let searched = $state(false);
	let loading = $state(false);
	let error = $state('');
	let locating = $state(false);
	let nearbyMode = $state(false);

	let debounceTimer: ReturnType<typeof setTimeout> | null = null;

	import { authStore } from '$lib/stores/auth.store.svelte';

	$effect(() => {
		if (authStore.isAuthenticated) {
			restaurantsService.cuisines().then((c) => (cuisines = c)).catch(() => {});
		}
	});

	function getCurrentPosition(): Promise<GeolocationPosition> {
		return new Promise((resolve, reject) => {
			if (!browser || !navigator.geolocation) {
				reject(new Error('Geolocation not available'));
				return;
			}
			navigator.geolocation.getCurrentPosition(resolve, reject, {
				enableHighAccuracy: false,
				timeout: 10000,
				maximumAge: 60000,
			});
		});
	}

	async function loadNearby() {
		loading = true;
		locating = true;
		error = '';
		searched = true;
		nearbyMode = true;
		try {
			const pos = await getCurrentPosition();
			locating = false;
			const nearby = await restaurantsService.nearby(
				pos.coords.latitude,
				pos.coords.longitude,
				20
			);
			results = nearby;
		} catch (err: unknown) {
			locating = false;
			const msg = err instanceof Error ? err.message : '';
			if (msg.includes('denied') || msg.includes('not available')) {
				error = 'Location permission denied. Try searching by name or city instead.';
			} else {
				error = 'Could not get your location. Try searching manually.';
			}
			results = [];
		} finally {
			loading = false;
		}
	}

	async function runSearch() {
		const params: { search?: string; city?: string; cuisine?: string } = {};
		if (query.trim()) params.search = query.trim();
		if (cityFilter.trim()) params.city = cityFilter.trim();
		if (cuisineFilter) params.cuisine = cuisineFilter;

		// No filters → fall back to nearby
		if (Object.keys(params).length === 0) {
			await loadNearby();
			return;
		}

		loading = true;
		error = '';
		searched = true;
		nearbyMode = false;
		try {
			const res = await restaurantsService.list(params);
			results = res.results;
		} catch {
			error = 'Could not load results.';
			results = [];
		} finally {
			loading = false;
		}
	}

	function onInputChange() {
		// Only auto-search when there's actually something to filter.
		// Otherwise the user has to press Enter / the Search button so we don't
		// trigger a geolocation prompt on every keystroke.
		if (debounceTimer) clearTimeout(debounceTimer);
		if (hasFilters) {
			debounceTimer = setTimeout(runSearch, 350);
		}
	}

	function clearAll() {
		query = '';
		cityFilter = '';
		cuisineFilter = '';
		results = [];
		searched = false;
		nearbyMode = false;
	}

	const hasFilters = $derived(
		query.trim().length > 0 || cityFilter.trim().length > 0 || cuisineFilter.length > 0
	);

	const validResults = $derived(results.filter((r) => r.lat && r.lng));

	async function onMapReady(map: L.Map) {
		if (!browser || validResults.length === 0) return;

		const leaflet = await import('leaflet');
		const L = leaflet.default;
		const bounds: [number, number][] = [];

		for (const r of validResults) {
			const icon = L.divIcon({
				className: '',
				html: `<div style="width:28px;height:28px;background:#2D6A4F;border:3px solid white;border-radius:50%;box-shadow:0 2px 6px rgba(0,0,0,0.2);"></div>`,
				iconSize: [28, 28],
				iconAnchor: [14, 14],
			});

			L.marker([r.lat, r.lng], { icon })
				.addTo(map)
				.bindPopup(`
					<div style="font-family:Inter,sans-serif;min-width:140px;">
						<strong style="font-size:14px;">${r.name}</strong>
						${r.city ? `<br><span style="color:#8A8A8A;font-size:12px;">${r.city}</span>` : ''}
						${r.cuisineDetail ? `<br><span style="color:#8A8A8A;font-size:11px;">${r.cuisineDetail.name}</span>` : ''}
						${r.averageRating ? `<br><span style="color:#2D6A4F;font-size:13px;">★ ${r.averageRating.toFixed(1)}</span>` : ''}
						${dietaryBadgesHtml(r.tagsDetail)}
					</div>
				`);
			bounds.push([r.lat, r.lng]);
		}

		if (bounds.length > 0) {
			map.fitBounds(bounds, { padding: [40, 40], maxZoom: 14 });
		}
	}

	function priceLabel(level: number | null): string {
		return level ? '$'.repeat(level) : '';
	}
</script>

<div class="flex h-full flex-col">
	<header class="shrink-0 px-5 pb-3 pt-4">
		<h1 class="mb-3 text-lg font-semibold text-ink">{t('search.title')}</h1>

		<!-- Search input -->
		<div class="relative">
			<svg class="absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-ink-muted" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
				<circle cx="11" cy="11" r="8" /><path d="m21 21-4.35-4.35" />
			</svg>
			<input
				type="search"
				bind:value={query}
				oninput={onInputChange}
				onkeydown={(e) => e.key === 'Enter' && runSearch()}
				placeholder={t('search.placeholder')}
				class="w-full rounded-input border border-cream-dark bg-white py-3 pl-10 pr-4 text-base text-ink outline-none focus:border-jade"
			/>
		</div>

		<!-- Filters row -->
		<div class="mt-2 flex gap-2">
			<input
				type="text"
				bind:value={cityFilter}
				oninput={onInputChange}
				onkeydown={(e) => e.key === 'Enter' && runSearch()}
				placeholder={t('search.city')}
				class="min-w-0 flex-1 rounded-input border border-cream-dark bg-white px-3 py-2.5 text-base text-ink outline-none focus:border-jade"
			/>
			<select
				bind:value={cuisineFilter}
				onchange={runSearch}
				class="min-w-0 flex-1 rounded-input border border-cream-dark bg-white px-3 py-2.5 text-base text-ink outline-none focus:border-jade"
			>
				<option value="">{t('search.anyCuisine')}</option>
				{#each cuisines as c}
					<option value={c.slug}>{c.name}</option>
				{/each}
			</select>
		</div>

		<!-- Search button (always visible, behaviour depends on filters) -->
		<button
			onclick={runSearch}
			disabled={loading}
			class="mt-2 flex min-h-11 w-full items-center justify-center gap-2 rounded-button bg-jade text-sm font-semibold text-white active:scale-[0.98] disabled:opacity-50"
		>
			{#if hasFilters}
				<svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
					<circle cx="11" cy="11" r="8" /><path d="m21 21-4.35-4.35" />
				</svg>
				{t('search.search')}
			{:else}
				<svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
					<path d="M12 13a3 3 0 1 0 0-6 3 3 0 0 0 0 6Z" />
					<path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7Z" />
				</svg>
				{t('search.findNearby')}
			{/if}
		</button>

		<!-- View toggle + clear -->
		{#if searched && results.length > 0}
			<div class="mt-3 flex items-center gap-2">
				<div class="flex flex-1 gap-1 rounded-card bg-cream-dark p-1">
					<button
						onclick={() => (view = 'list')}
						class="flex-1 rounded-button py-1.5 text-sm font-medium active:scale-[0.98]
							{view === 'list' ? 'bg-white text-ink shadow-card' : 'text-ink-muted'}"
					>
						{t('search.list')}
					</button>
					<button
						onclick={() => (view = 'map')}
						class="flex-1 rounded-button py-1.5 text-sm font-medium active:scale-[0.98]
							{view === 'map' ? 'bg-white text-ink shadow-card' : 'text-ink-muted'}"
					>
						{t('search.map')}
					</button>
				</div>
				{#if hasFilters}
					<button
						onclick={clearAll}
						class="flex min-h-9 items-center gap-1 rounded-button border border-cream-dark px-3 text-xs font-medium text-ink-muted active:scale-[0.98]"
					>
						{t('search.clear')}
					</button>
				{/if}
			</div>
		{/if}
	</header>

	<!-- Results -->
	<div class="min-h-0 flex-1">
		{#if loading}
			<div class="flex h-full flex-col items-center justify-center gap-3">
				<div class="h-7 w-7 animate-spin rounded-full border-2 border-jade border-t-transparent"></div>
				{#if locating}
					<p class="text-xs text-ink-muted">{t('search.gettingLocation')}</p>
				{/if}
			</div>

		{:else if error}
			<div class="flex h-full flex-col items-center justify-center px-6 text-center">
				<p class="text-sm text-blush">{error}</p>
				<button onclick={runSearch} class="mt-3 text-sm font-medium text-jade active:opacity-70">
					Try again
				</button>
			</div>

		{:else if !searched}
			<div class="flex h-full flex-col items-center justify-center px-8 text-center">
				<div class="mb-3 flex h-14 w-14 items-center justify-center rounded-full bg-jade/10 text-jade">
					<svg class="h-7 w-7" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
						<circle cx="11" cy="11" r="8" /><path d="m21 21-4.3-4.3" />
					</svg>
				</div>
				<p class="text-sm font-medium text-ink">{t('search.findRestaurants')}</p>
				<p class="mt-1 text-xs text-ink-muted">
					Press <span class="font-medium text-ink">Find nearby</span> to see what's around you,<br />
					or filter by name, city or cuisine.
				</p>
			</div>

		{:else if results.length === 0}
			<div class="flex h-full flex-col items-center justify-center px-8 text-center">
				<p class="text-sm font-medium text-ink">{t('search.noResults')}</p>
				<p class="mt-1 text-xs text-ink-muted">{t('search.noResultsDesc')}</p>
			</div>

		{:else if view === 'list'}
			<ul class="h-full space-y-2 overflow-y-auto px-5 pb-6 pt-3">
				{#if nearbyMode}
					<li class="flex items-center gap-2 rounded-card bg-jade/10 px-3 py-2 text-xs font-medium text-jade">
						<svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
							<path d="M12 13a3 3 0 1 0 0-6 3 3 0 0 0 0 6Z" />
							<path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7Z" />
						</svg>
						{t('search.nearYou')}
					</li>
				{/if}
				{#each results as r (r.id)}
					<li>
						<button
							type="button"
							onclick={() => viewRestaurant(r)}
							class="flex w-full overflow-hidden rounded-card bg-white text-left shadow-card active:scale-[0.98]"
						>
							{#if r.imageUrl}
								<img
									src={r.imageUrl}
									alt={r.name}
									class="h-28 w-24 shrink-0 object-cover"
									loading="lazy"
								/>
							{/if}
							<div class="flex min-w-0 flex-1 flex-col justify-center gap-1 p-3">
								<p class="truncate text-sm font-semibold text-ink">{r.name}</p>
								<p class="flex flex-wrap items-center gap-1 text-xs text-ink-muted">
									{#if r.city}<span>{r.city}</span>{/if}
									{#if r.cuisineDetail}
										<span>·</span>
										<span>{r.cuisineDetail.name}</span>
									{/if}
									{#if r.priceLevel}
										<span>·</span>
										<span>{priceLabel(r.priceLevel)}</span>
									{/if}
								</p>
								{#if r.averageRating}
									<div class="flex items-center gap-1.5">
										<div class="flex text-amber-400">
											{#each Array(5) as _, i}
												{#if i < Math.round(r.averageRating ?? 0)}
													<svg class="h-3.5 w-3.5" viewBox="0 0 20 20" fill="currentColor"><path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z"/></svg>
												{:else}
													<svg class="h-3.5 w-3.5 text-cream-dark" viewBox="0 0 20 20" fill="currentColor"><path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z"/></svg>
												{/if}
											{/each}
										</div>
										<span class="text-xs text-ink-muted">{r.averageRating.toFixed(1)}</span>
										<span class="text-xs text-ink-muted">({r.pinCount})</span>
									</div>
								{:else if r.pinCount > 0}
									<p class="text-xs text-ink-muted">{r.pinCount} pin{r.pinCount === 1 ? '' : 's'}</p>
								{/if}
								{#if r.tagsDetail?.length}
									<DietaryBadges tags={r.tagsDetail} />
								{/if}
							</div>
						</button>
					</li>
				{/each}
			</ul>

		{:else}
			{#key validResults.length + '-' + query + '-' + cityFilter + '-' + cuisineFilter}
				<MapView center={[20, 0]} zoom={2} autoLocate={false} {onMapReady} />
			{/key}
		{/if}
	</div>
</div>
