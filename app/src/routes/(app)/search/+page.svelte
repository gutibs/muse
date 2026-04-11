<script lang="ts">
	import { browser } from '$app/environment';
	import { goto } from '$app/navigation';
	import MapView from '$lib/components/MapView.svelte';
	import { restaurantsService } from '$lib/services/restaurants.service';
	import type { Cuisine, Restaurant } from '$lib/types';
	import type L from 'leaflet';

	function viewOnMap(r: Restaurant) {
		if (!r.lat || !r.lng) return;
		goto(`/map?focus=${r.id}`);
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
		<h1 class="mb-3 text-lg font-semibold text-ink">Search</h1>

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
				placeholder="Restaurant name..."
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
				placeholder="City"
				class="min-w-0 flex-1 rounded-input border border-cream-dark bg-white px-3 py-2.5 text-base text-ink outline-none focus:border-jade"
			/>
			<select
				bind:value={cuisineFilter}
				onchange={runSearch}
				class="min-w-0 flex-1 rounded-input border border-cream-dark bg-white px-3 py-2.5 text-base text-ink outline-none focus:border-jade"
			>
				<option value="">Any cuisine</option>
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
				Search
			{:else}
				<svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
					<path d="M12 13a3 3 0 1 0 0-6 3 3 0 0 0 0 6Z" />
					<path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7Z" />
				</svg>
				Find nearby
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
						List
					</button>
					<button
						onclick={() => (view = 'map')}
						class="flex-1 rounded-button py-1.5 text-sm font-medium active:scale-[0.98]
							{view === 'map' ? 'bg-white text-ink shadow-card' : 'text-ink-muted'}"
					>
						Map
					</button>
				</div>
				{#if hasFilters}
					<button
						onclick={clearAll}
						class="flex min-h-9 items-center gap-1 rounded-button border border-cream-dark px-3 text-xs font-medium text-ink-muted active:scale-[0.98]"
					>
						Clear
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
					<p class="text-xs text-ink-muted">Getting your location...</p>
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
				<p class="text-sm font-medium text-ink">Find restaurants</p>
				<p class="mt-1 text-xs text-ink-muted">
					Press <span class="font-medium text-ink">Find nearby</span> to see what's around you,<br />
					or filter by name, city or cuisine.
				</p>
			</div>

		{:else if results.length === 0}
			<div class="flex h-full flex-col items-center justify-center px-8 text-center">
				<p class="text-sm font-medium text-ink">No restaurants found</p>
				<p class="mt-1 text-xs text-ink-muted">Try different filters or check the spelling</p>
			</div>

		{:else if view === 'list'}
			<ul class="h-full space-y-2 overflow-y-auto px-5 pb-6 pt-3">
				{#if nearbyMode}
					<li class="flex items-center gap-2 rounded-card bg-jade/10 px-3 py-2 text-xs font-medium text-jade">
						<svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
							<path d="M12 13a3 3 0 1 0 0-6 3 3 0 0 0 0 6Z" />
							<path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7Z" />
						</svg>
						Showing restaurants near you (~20km)
					</li>
				{/if}
				{#each results as r (r.id)}
					<li>
						<button
							type="button"
							onclick={() => viewOnMap(r)}
							class="flex w-full items-start gap-3 rounded-card bg-white p-4 text-left shadow-card active:scale-[0.98]"
						>
							<div class="min-w-0 flex-1">
								<p class="truncate text-sm font-semibold text-ink">{r.name}</p>
								<p class="mt-0.5 flex flex-wrap items-center gap-1 text-xs text-ink-muted">
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
									<p class="mt-1 text-sm text-amber-500">
										★ <span class="text-xs text-ink-muted">{r.averageRating.toFixed(1)} ({r.pinCount} pin{r.pinCount === 1 ? '' : 's'})</span>
									</p>
								{:else if r.pinCount > 0}
									<p class="mt-1 text-xs text-ink-muted">{r.pinCount} pin{r.pinCount === 1 ? '' : 's'}</p>
								{/if}
							</div>
							<svg class="mt-1 h-4 w-4 shrink-0 text-ink-muted" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
								<path d="M12 13a3 3 0 1 0 0-6 3 3 0 0 0 0 6Z" />
								<path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7Z" />
							</svg>
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
