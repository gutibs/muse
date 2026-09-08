<script lang="ts">
	import { goto } from '$app/navigation';
	import CityAutocomplete from '$lib/components/CityAutocomplete.svelte';
	import InsiderBadge from '$lib/components/InsiderBadge.svelte';
	import DietaryBadges from '$lib/components/DietaryBadges.svelte';
	import GoogleSuggestions from '$lib/components/GoogleSuggestions.svelte';
	import PinsMap, { type MapItem } from '$lib/components/PinsMap.svelte';
	import { t } from '$lib/i18n/index.svelte';
	import { googleImportErrorKey, importPlace } from '$lib/services/google-import';
	import { placesService, type PlaceSuggestion } from '$lib/services/places.service';
	import { restaurantsService } from '$lib/services/restaurants.service';
	import type { Cuisine, Restaurant } from '$lib/types';
	import { ApiError } from '$lib/types';
	import { extractFirstDrfError } from '$lib/utils/api-error';
	import { getCurrentPosition, GeoError } from '$lib/utils/geolocate';
	import { readGoogleSuggestions } from '$lib/utils/google-suggestions';

	function viewRestaurant(r: Restaurant) {
		goto(`/restaurant/${r.id}`);
	}

	let query = $state('');
	let cityFilter = $state('');
	let cuisineFilter = $state('');
	let insiderOnly = $state(false);

	function toggleInsiderOnly() {
		insiderOnly = !insiderOnly;
		runSearch();
	}

	let cuisines = $state<Cuisine[]>([]);
	let results = $state<Restaurant[]>([]);
	let googleResults = $state<PlaceSuggestion[]>([]);
	let googleFailed = $state(false);
	let googleMessageKey = $state<string | null>(null);
	let importingPlaceId = $state<string | null>(null);
	let view = $state<'list' | 'map'>('list');

	let searched = $state(false);
	let loading = $state(false);
	let error = $state('');
	let locating = $state(false);
	let nearbyMode = $state(false);

	let debounceTimer: ReturnType<typeof setTimeout> | null = null;

	import { authStore } from '$lib/stores/auth.store.svelte';
	import { logSilent } from '$lib/utils/logger';
	import RatingHearts from '$lib/components/RatingHearts.svelte';
	import PinCard from '$lib/components/PinCard.svelte';
	import { trackVenueCardView } from '$lib/services/analytics.service';

	$effect(() => {
		if (authStore.isAuthenticated && cuisines.length === 0) {
			loadCuisines();
		}
	});

	async function loadCuisines(retry = true) {
		try {
			cuisines = await restaurantsService.cuisines();
		} catch (err) {
			logSilent('search:cuisines', err);
			if (retry) setTimeout(() => loadCuisines(false), 1500);
		}
	}

	async function loadNearby() {
		loading = true;
		locating = true;
		error = '';
		searched = true;
		nearbyMode = true;
		try {
			const pos = await getCurrentPosition({
				enableHighAccuracy: false,
				timeout: 10000,
				maximumAge: 60000,
			});
			locating = false;
			const nearby = await restaurantsService.nearby(pos.latitude, pos.longitude, 20);
			results = nearby;
		} catch (err: unknown) {
			locating = false;
			if (err instanceof GeoError) {
				if (err.code === 'permission_denied' || err.code === 'not_available') {
					error = t('search.locationDenied');
				} else {
					error = t('search.cantGetLocation');
				}
			} else {
				error = t('search.cantGetLocation');
			}
			results = [];
		} finally {
			loading = false;
		}
	}

	async function runSearch() {
		const params: { search?: string; city?: string; cuisine?: string; insider?: boolean } = {};
		if (query.trim()) params.search = query.trim();
		if (cityFilter.trim()) params.city = cityFilter.trim();
		if (cuisineFilter) params.cuisine = cuisineFilter;
		if (insiderOnly) params.insider = true;

		// No filters → fall back to nearby
		if (Object.keys(params).length === 0) {
			await loadNearby();
			return;
		}

		loading = true;
		error = '';
		searched = true;
		nearbyMode = false;
		googleResults = [];
		googleFailed = false;
		googleMessageKey = null;
		try {
			// Only ask Google for suggestions when the user is actually typing a
			// restaurant name. Searching Google with just a city returns places
			// *named* after that city, which is confusing (see Jess feedback).
			const hasNameQuery = query.trim().length > 0;
			const googleQuery = hasNameQuery
				? [query.trim(), cityFilter.trim()].filter(Boolean).join(' ')
				: '';
			const [dbRes, placesRes] = await Promise.allSettled([
				restaurantsService.list(params),
				googleQuery ? placesService.autocomplete(googleQuery) : Promise.resolve({ results: [] }),
			]);
			results = dbRes.status === 'fulfilled' ? dbRes.value.results : [];
			const google = readGoogleSuggestions(placesRes, 'search:google');
			googleResults = google.results;
			googleFailed = google.failed;
			googleMessageKey = google.messageKey;
		} catch (err) {
			error = t('search.cantLoadResults');
			results = [];
			logSilent('search:load', err);
		} finally {
			loading = false;
		}
	}

	async function importFromGoogle(suggestion: PlaceSuggestion) {
		importingPlaceId = suggestion.placeId;
		try {
			const restaurant = await importPlace(suggestion.placeId);
			goto(`/restaurant/${restaurant.id}`);
		} catch (err) {
			const key = googleImportErrorKey(err);
			error = key
				? t(key)
				: extractFirstDrfError(err as ApiError, t('search.cantImport'));
		} finally {
			importingPlaceId = null;
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

	const mapItems = $derived<MapItem[]>(
		validResults.map((r) => ({ kind: 'restaurant', restaurant: r }))
	);

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

		<!-- City filter (with autocomplete dropdown) -->
		<div class="mt-2">
			<CityAutocomplete
				bind:value={cityFilter}
				placeholder={t('search.city')}
				onPick={() => runSearch()}
				onSubmit={() => runSearch()}
			/>
		</div>

		<!-- Sólo recomendados por Insiders. Es un eje más y se cruza con los
		     otros: el backend los combina con AND. -->
		<div class="mt-2">
			<button
				onclick={toggleInsiderOnly}
				aria-pressed={insiderOnly}
				class="flex w-fit items-center gap-1.5 rounded-full px-3 py-1.5 text-xs font-medium active:scale-95
					{insiderOnly ? 'bg-jade-dark text-white' : 'border border-cream-dark bg-white text-ink-muted'}"
			>
				<InsiderBadge size="sm" labelled={false} tone={insiderOnly ? 'inherit' : 'brand'} />
				{t('search.insiderOnly')}
			</button>
		</div>

		<!-- Cuisine filter -->
		<div class="mt-2">
			<select
				bind:value={cuisineFilter}
				onchange={runSearch}
				class="w-full rounded-input border border-cream-dark bg-white px-3 py-2.5 text-base text-ink outline-none focus:border-jade"
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
					{t('common.tryAgain')}
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
				<p class="mt-1 text-xs text-ink-muted">{t('search.findInstructions').split('{button}')[0]}<span class="font-medium text-ink">{t('search.findNearby')}</span>{t('search.findInstructions').split('{button}')[1] || ''}</p>
			</div>

		{:else if results.length === 0 && googleResults.length === 0}
			{#if googleFailed}
				<GoogleSuggestions
					results={[]}
					failed={true}
					messageKey={googleMessageKey}
					title=""
					centered={true}
				/>
			{:else}
				<div class="flex h-full flex-col items-center justify-center px-8 text-center">
					<p class="text-sm font-medium text-ink">{t('search.notOnList')}</p>
					<p class="mt-1 text-xs text-ink-muted">{t('search.notOnListDesc')}</p>
				</div>
			{/if}

		{:else if view === 'list'}
			<div class="h-full space-y-2 overflow-y-auto px-5 pb-6 pt-3">
			<ul class="space-y-2">
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
						<PinCard
							onclick={() => viewRestaurant(r)}
							onVisible={() => trackVenueCardView(r.id, 'search')}
							imageUrl={r.imageUrl}
							imageAlt={r.name}
						>
							<p class="truncate text-sm font-semibold text-ink">{r.name}</p>
							<p class="flex flex-wrap items-center gap-1 text-xs text-ink-muted">
								{#if r.city}<span>{r.city}</span>{/if}
								{#if r.cuisinesDetail?.length}
									<span>·</span>
									<span>{r.cuisinesDetail.map((c) => c.name).join(', ')}</span>
								{/if}
								{#if r.priceLevel}
									<span>·</span>
									<span>{priceLabel(r.priceLevel)}</span>
								{/if}
							</p>
							{#if r.averageRating}
								<div class="flex items-center gap-1.5">
									<RatingHearts value={Math.round(r.averageRating ?? 0)} />
									<span class="text-xs text-ink-muted">{r.averageRating.toFixed(1)}</span>
									<span class="text-xs text-ink-muted">({r.pinCount})</span>
								</div>
							{:else}
								<p class="text-xs italic text-ink-muted">{t('search.notRatedYet')}</p>
							{/if}
							{#if r.address}
								<p class="truncate text-xs text-ink-muted">{r.address}</p>
							{/if}
							{#if r.tagsDetail?.length}
								<DietaryBadges tags={r.tagsDetail} />
							{/if}
						</PinCard>
					</li>
				{/each}

			</ul>

			<GoogleSuggestions
				results={googleResults}
				failed={googleFailed}
				messageKey={googleMessageKey}
				title={t('search.fromGoogleNotOnMuse')}
				{importingPlaceId}
				onselect={importFromGoogle}
			/>
			</div>

		{:else}
			<PinsMap items={mapItems} accent="visited" link={false} showDietary={true} />
		{/if}
	</div>
</div>
