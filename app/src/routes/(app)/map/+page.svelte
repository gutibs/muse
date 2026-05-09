<script lang="ts">
	import { browser } from '$app/environment';
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import CityAutocomplete from '$lib/components/CityAutocomplete.svelte';
	import MapView from '$lib/components/MapView.svelte';
	import { t } from '$lib/i18n/index.svelte';
	import { friendsService } from '$lib/services/friends.service';
	import { pinsService } from '$lib/services/pins.service';
	import { placesService } from '$lib/services/places.service';
	import { restaurantsService } from '$lib/services/restaurants.service';
	import { usersService } from '$lib/services/users.service';
	import { authStore } from '$lib/stores/auth.store.svelte';
	import type { Pin } from '$lib/types';
	import { escapeHtml } from '$lib/utils/escape-html';
	import { getOtherUser } from '$lib/utils/friendship';
	import { createPinIcon, PIN_COLORS } from '$lib/utils/map';
	import type L from 'leaflet';

	let hasFocus = $derived(Boolean(page.url.searchParams.get('focus')));
	let showFriendPins = $state(true);
	let showSearch = $state(false);
	let friendLayers = $state<L.LayerGroup | null>(null);
	let mapRef = $state<L.Map | null>(null);
	let friendCount = $state(0);

	// Track markers with their cuisine slugs for filtering
	type MarkerEntry = { marker: L.Marker; cuisineSlugs: string[]; isFriend: boolean };
	let allMarkers = $state<MarkerEntry[]>([]);

	// Map search
	let citySearch = $state('');
	let cuisineSearch = $state('');
	let searching = $state(false);
	let cuisinesList = $state<{ id: number; name: string; slug: string }[]>([]);

	$effect(() => {
		if (authStore.isAuthenticated && cuisinesList.length === 0) {
			loadCuisines();
		}
	});

	// Cuisines fetch silently failing leaves the search dropdown empty (only
	// "Any cuisine" visible), which is a confusing UX. Log the failure and
	// retry once after a short delay so transient errors don't kill the flow.
	async function loadCuisines(retry = true) {
		try {
			cuisinesList = await restaurantsService.cuisines();
		} catch (err) {
			console.warn('[map] cuisines fetch failed', err);
			if (retry) setTimeout(() => loadCuisines(false), 1500);
		}
	}

	function applyMarkerFilter() {
		if (!mapRef) return;
		const cuisineFilter = cuisineSearch;
		for (const entry of allMarkers) {
			const matches = !cuisineFilter || entry.cuisineSlugs.includes(cuisineFilter);
			const shouldShow = matches && (!entry.isFriend || showFriendPins);
			// Friend markers live inside friendLayers (a LayerGroup); own markers live on the map.
			const container: L.Map | L.LayerGroup | null = entry.isFriend ? friendLayers : mapRef;
			if (!container) continue;
			const isPresent = container.hasLayer(entry.marker);
			if (shouldShow && !isPresent) {
				container.addLayer(entry.marker);
			} else if (!shouldShow && isPresent) {
				container.removeLayer(entry.marker);
			}
		}
	}

	async function mapSearch() {
		if (!mapRef) return;
		const hasCityQuery = citySearch.trim().length > 0;
		const hasCuisineQuery = cuisineSearch.length > 0;

		if (!hasCityQuery && !hasCuisineQuery) return;

		searching = true;
		try {
			// If city query, ask the backend for matching cities (filtered by
			// type=city) and fly to the first hit. Avoids the previous bug where
			// Nominatim returned random places (streets, monuments) for any text.
			if (hasCityQuery) {
				try {
					const res = await placesService.cityAutocomplete(citySearch.trim());
					const first = res.results?.[0];
					if (first) {
						const details = await placesService.details(first.placeId);
						mapRef.setView([details.lat, details.lng], 13, { animate: true });
					}
				} catch {
					// silent fail — search bar stays open for retry
				}
			}

			// Filter visible markers by cuisine
			applyMarkerFilter();

			// If cuisine filter narrows things, fit map to matching markers
			if (hasCuisineQuery && !hasCityQuery) {
				const bounds: [number, number][] = [];
				for (const entry of allMarkers) {
					if (entry.cuisineSlugs.includes(cuisineSearch) && mapRef.hasLayer(entry.marker)) {
						bounds.push([entry.marker.getLatLng().lat, entry.marker.getLatLng().lng]);
					}
				}
				if (bounds.length > 0) {
					mapRef.fitBounds(bounds, { padding: [40, 40], maxZoom: 14 });
				}
			}
		} catch {
			// silent fail
		} finally {
			searching = false;
		}
	}

	async function loadFriendPins(map: L.Map, Leaflet: typeof L, markersById?: Map<number, L.Marker>) {
		try {
			const friendships = await friendsService.list();
			friendCount = friendships.length;
			const myId = authStore.user?.id ?? 0;

			const group = Leaflet.layerGroup();

			for (const f of friendships) {
				const other = getOtherUser(f, myId);
				try {
					const pins = await usersService.getPins(other.id);
					for (const pin of pins) {
						const r = pin.restaurantDetail;
						if (!r?.lat || !r?.lng) continue;

						const icon = createPinIcon(Leaflet, PIN_COLORS.friend);

						const marker = Leaflet.marker([r.lat, r.lng], { icon })
							.addTo(group)
							.bindPopup(`
								<div style="font-family:Inter,sans-serif;min-width:140px;">
									<span style="color:#AF9483;font-size:11px;font-weight:600;">${escapeHtml(other.displayName || other.email)}</span>
									<br><a href="/restaurant/${r.id}" style="font-size:14px;font-weight:700;color:#2B221A;text-decoration:none;">${escapeHtml(r.name)}</a>
									${r.city ? `<br><span style="color:#9A8E7E;font-size:12px;">${escapeHtml(r.city)}</span>` : ''}
									${pin.rating ? `<br><span style="color:#8A7363;font-size:13px;">♥ ${pin.rating}/5</span>` : ''}
								</div>
							`);
						// Only register if not already present (own pins take priority)
						if (markersById && !markersById.has(r.id)) {
							markersById.set(r.id, marker);
						}
						allMarkers.push({
							marker,
							cuisineSlugs: (r.cuisinesDetail ?? []).map((c) => c.slug),
							isFriend: true,
						});
					}
				} catch {
					// friend might have no pins or permission error
				}
			}

			friendLayers = group;
			if (showFriendPins) group.addTo(map);
		} catch {
			// no friends yet
		}
	}

	function toggleFriendPins() {
		showFriendPins = !showFriendPins;
		if (!mapRef || !friendLayers) return;
		if (showFriendPins) friendLayers.addTo(mapRef);
		else friendLayers.removeFrom(mapRef);
	}

	async function onMapReady(map: L.Map) {
		if (!browser) return;
		mapRef = map;

		const pinsRes = await pinsService.list().catch(() => ({ results: [] as Pin[] }));

		const pins = pinsRes.results;

		const leaflet = await import('leaflet');
		const L = leaflet.default;

		const markersById = new Map<number, L.Marker>();
		allMarkers = [];

		// Only show restaurants that the user has pinned (rated or on the list)
		for (const pin of pins) {
			const r = pin.restaurantDetail;
			if (!r?.lat || !r?.lng) continue;

			const color = pin.status === 'visited' ? PIN_COLORS.visited : PIN_COLORS.toVisit;
			const icon = createPinIcon(L, color);

			const marker = L.marker([r.lat, r.lng], { icon })
				.addTo(map)
				.bindPopup(`
					<div style="font-family:Inter,sans-serif;min-width:140px;">
						<a href="/restaurant/${r.id}" style="font-size:14px;font-weight:700;color:#2B221A;text-decoration:none;">${escapeHtml(r.name)}</a>
						${r.city ? `<br><span style="color:#9A8E7E;font-size:12px;">${escapeHtml(r.city)}</span>` : ''}
						${pin.rating ? `<br><span style="color:#8A7363;font-size:13px;">♥ ${pin.rating}/5</span>` : ''}
						<br><span style="color:#9A8E7E;font-size:11px;">${pin.status === 'visited' ? t('map.popupRated') : t('map.popupOnList')}</span>
					</div>
				`);
			markersById.set(r.id, marker);
			allMarkers.push({
				marker,
				cuisineSlugs: (r.cuisinesDetail ?? []).map((c) => c.slug),
				isFriend: false,
			});
		}

		const focusId = Number(page.url.searchParams.get('focus'));
		function tryFocus() {
			if (!focusId) return false;
			const target = markersById.get(focusId);
			if (target) {
				map.setView(target.getLatLng(), 17, { animate: true });
				target.openPopup();
				return true;
			}
			return false;
		}

		// Try focusing on user's own pins first
		const focused = tryFocus();

		// Fallback: if no focus param and geolocation hasn't kicked in within 3s,
		// fit the view to the user's own pins (or all pins after friends load).
		// This prevents the map from sitting on the default world view when the
		// user denies location or the device fails to determine it.
		// Only locationfound counts as "decided" — on error we still want to fit to pins.
		let geolocationFound = false;
		map.once('locationfound', () => { geolocationFound = true; });

		const fitToOwnPins = () => {
			if (focused || geolocationFound || hasFocus) return;
			const own = allMarkers.filter((m) => !m.isFriend).map((m) => m.marker.getLatLng());
			if (own.length === 0) return;
			const bounds = L.latLngBounds(own);
			map.fitBounds(bounds, { padding: [40, 40], maxZoom: 14 });
		};

		setTimeout(fitToOwnPins, 3000);

		// Load friend pins and retry focus if not yet found
		loadFriendPins(map, L, markersById).then(() => {
			if (!focused) tryFocus();
		});
	}
</script>

<div class="relative h-full w-full">
	<MapView center={[51.505, -0.09]} zoom={3} autoLocate={!hasFocus} {onMapReady} />

	<!-- Search bar + controls -->
	<div class="absolute left-4 right-4 z-1000 space-y-2" style="top: calc(var(--sat, 0px) + 1rem);">
		{#if showSearch}
			<div class="rounded-card bg-white p-2 shadow-elevated">
				<div class="flex gap-2">
					<div class="min-w-0 flex-1">
						<CityAutocomplete
							bind:value={citySearch}
							placeholder={t('search.city')}
							onPick={() => mapSearch()}
						/>
					</div>
					<button
						onclick={mapSearch}
						disabled={searching || (!citySearch.trim() && !cuisineSearch)}
						class="flex min-h-10 items-center justify-center rounded-button bg-jade px-3 text-white active:scale-95 disabled:opacity-40"
					>
						{#if searching}
							<div class="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent"></div>
						{:else}
							<svg class="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
								<circle cx="11" cy="11" r="8" /><path d="m21 21-4.35-4.35" />
							</svg>
						{/if}
					</button>
					<button
						onclick={() => { showSearch = false; citySearch = ''; cuisineSearch = ''; }}
						aria-label={t('search.clear')}
						class="flex min-h-10 items-center justify-center rounded-button bg-cream-dark px-2 text-ink-muted active:scale-95"
					>
						<svg class="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
							<line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" />
						</svg>
					</button>
				</div>
				<select
					bind:value={cuisineSearch}
					onchange={mapSearch}
					class="mt-2 w-full rounded-input border border-cream-dark bg-white px-3 py-2 text-base text-ink outline-none focus:border-jade"
				>
					<option value="">{t('search.anyCuisine')}</option>
					{#each cuisinesList as c}
						<option value={c.slug}>{c.name}</option>
					{/each}
				</select>
			</div>
		{:else}
			<button
				onclick={() => (showSearch = true)}
				class="flex h-10 items-center gap-2 rounded-full bg-white px-4 shadow-elevated active:scale-95"
			>
				<svg class="h-4 w-4 text-ink-muted" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
					<circle cx="11" cy="11" r="8" /><path d="m21 21-4.35-4.35" />
				</svg>
				<span class="text-sm text-ink-muted">{t('search.city')} / {t('search.anyCuisine')}</span>
			</button>
		{/if}

		<!-- Friend pins toggle (inside same container to avoid overlap) -->
		{#if friendCount > 0}
			<button
				onclick={toggleFriendPins}
				class="flex w-fit items-center gap-2 rounded-full px-3 py-2 text-xs font-medium shadow-elevated active:scale-95
					{showFriendPins ? 'bg-jade text-white' : 'bg-white/90 text-ink-muted border border-cream-dark'}"
			>
				<div class="flex h-5 w-9 items-center rounded-full p-0.5 transition-colors
					{showFriendPins ? 'bg-white/30 justify-end' : 'bg-cream-dark justify-start'}"
				>
					<div class="h-4 w-4 rounded-full bg-white shadow-card"></div>
				</div>
				{showFriendPins ? t('map.friendsOn') : t('map.friendsOff')}
			</button>
		{/if}
	</div>

	<!-- Legend — inline chips, always visible -->
	<div class="absolute left-4 z-1000 flex flex-wrap gap-1.5" style="bottom: calc(var(--sab, 0px) + 1rem);">
		<span class="flex items-center gap-1 rounded-full bg-white/90 px-2 py-1 text-[10px] font-medium text-ink shadow-card">
			<span class="inline-block h-2 w-2 rounded-full" style="background:{PIN_COLORS.visited};"></span>{t('map.yourVisited', { name: authStore.user?.displayName || 'You' })}
		</span>
		<span class="flex items-center gap-1 rounded-full bg-white/90 px-2 py-1 text-[10px] font-medium text-ink shadow-card">
			<span class="inline-block h-2 w-2 rounded-full" style="background:{PIN_COLORS.toVisit};"></span>{t('map.yourToVisit', { name: authStore.user?.displayName || 'You' })}
		</span>
		{#if friendCount > 0}
			<span class="flex items-center gap-1 rounded-full bg-white/90 px-2 py-1 text-[10px] font-medium text-ink shadow-card">
				<span class="inline-block h-2 w-2 rounded-full" style="background:{PIN_COLORS.friend};"></span>{t('map.friendPins')}
			</span>
		{/if}
	</div>

	<!-- FAB: Add Pin -->
	<button
		aria-label={t('home.addPin')}
		onclick={() => goto('/pin/new')}
		class="absolute right-4 z-1000 flex h-14 w-14 items-center justify-center rounded-full bg-jade text-white shadow-elevated active:scale-95"
		style="bottom: calc(var(--sab, 0px) + 6rem);"
	>
		<svg class="h-7 w-7" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
			<line x1="12" y1="5" x2="12" y2="19" />
			<line x1="5" y1="12" x2="19" y2="12" />
		</svg>
	</button>
</div>
