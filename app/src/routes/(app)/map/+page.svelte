<script lang="ts">
	import { browser } from '$app/environment';
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import MapView from '$lib/components/MapView.svelte';
	import { t } from '$lib/i18n/index.svelte';
	import { friendsService } from '$lib/services/friends.service';
	import { pinsService } from '$lib/services/pins.service';
	import { restaurantsService } from '$lib/services/restaurants.service';
	import { usersService } from '$lib/services/users.service';
	import { authStore } from '$lib/stores/auth.store.svelte';
	import type { Friendship, Pin, PublicUser, Restaurant } from '$lib/types';
	import type L from 'leaflet';

	let hasFocus = $derived(Boolean(page.url.searchParams.get('focus')));
	let showFriendPins = $state(true);
	let showSearch = $state(false);
	let friendLayers = $state<L.LayerGroup | null>(null);
	let mapRef = $state<L.Map | null>(null);
	let friendCount = $state(0);

	// Track markers with their cuisine slug for filtering
	type MarkerEntry = { marker: L.Marker; cuisineSlug: string; isFriend: boolean };
	let allMarkers = $state<MarkerEntry[]>([]);

	// Map search
	let citySearch = $state('');
	let cuisineSearch = $state('');
	let searching = $state(false);
	let cuisinesList = $state<{ id: number; name: string; slug: string }[]>([]);

	$effect(() => {
		if (authStore.isAuthenticated && cuisinesList.length === 0) {
			restaurantsService.cuisines().then((c) => (cuisinesList = c)).catch(() => {});
		}
	});

	function applyMarkerFilter() {
		if (!mapRef) return;
		const cuisineFilter = cuisineSearch;
		for (const entry of allMarkers) {
			// Friend pins also respect the showFriendPins toggle handled elsewhere;
			// only filter by cuisine here.
			const matches = !cuisineFilter || entry.cuisineSlug === cuisineFilter;
			if (matches) {
				// Add to map only if it's not already and (if friend) toggle is on
				if (!mapRef.hasLayer(entry.marker)) {
					if (!entry.isFriend || showFriendPins) entry.marker.addTo(mapRef);
				}
			} else {
				if (mapRef.hasLayer(entry.marker)) entry.marker.removeFrom(mapRef);
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
			// If city query, fly to that city
			if (hasCityQuery) {
				const res = await fetch(`https://nominatim.openstreetmap.org/search?q=${encodeURIComponent(citySearch.trim())}&format=json&limit=1`);
				const data = await res.json();
				if (data.length > 0) {
					const { lat, lon } = data[0];
					// Zoom to a city-level view that shows streets/neighborhoods
					mapRef.setView([parseFloat(lat), parseFloat(lon)], 13, { animate: true });
				}
			}

			// Filter visible markers by cuisine
			applyMarkerFilter();

			// If cuisine filter narrows things, fit map to matching markers
			if (hasCuisineQuery && !hasCityQuery) {
				const bounds: [number, number][] = [];
				for (const entry of allMarkers) {
					if (entry.cuisineSlug === cuisineSearch && mapRef.hasLayer(entry.marker)) {
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

	function getOtherUser(f: Friendship, myId: number): PublicUser {
		return f.fromUser.id === myId ? f.toUser : f.fromUser;
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

						const icon = Leaflet.divIcon({
							className: '',
							html: `<div style="width:28px;height:28px;background:#C9A678;border:3px solid white;border-radius:50%;box-shadow:0 2px 6px rgba(0,0,0,0.2);"></div>`,
							iconSize: [28, 28],
							iconAnchor: [14, 14],
						});

						const marker = Leaflet.marker([r.lat, r.lng], { icon })
							.addTo(group)
							.bindPopup(`
								<div style="font-family:Inter,sans-serif;min-width:140px;">
									<span style="color:#C9A678;font-size:11px;font-weight:600;">${other.displayName || other.email}</span>
									<br><a href="/restaurant/${r.id}" style="font-size:14px;font-weight:700;color:#1A1A1A;text-decoration:none;">${r.name}</a>
									${r.city ? `<br><span style="color:#9A8E7E;font-size:12px;">${r.city}</span>` : ''}
									${pin.rating ? `<br><span style="color:#5D4E3F;font-size:13px;">♥ ${pin.rating}/5</span>` : ''}
								</div>
							`);
						// Only register if not already present (own pins take priority)
						if (markersById && !markersById.has(r.id)) {
							markersById.set(r.id, marker);
						}
						allMarkers.push({
							marker,
							cuisineSlug: r.cuisineDetail?.slug || '',
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

			const color = pin.status === 'visited' ? '#5D4E3F' : '#9A8E7E';
			const icon = L.divIcon({
				className: '',
				html: `<div style="width:28px;height:28px;background:${color};border:3px solid white;border-radius:50%;box-shadow:0 2px 6px rgba(0,0,0,0.2);"></div>`,
				iconSize: [28, 28],
				iconAnchor: [14, 14],
			});

			const marker = L.marker([r.lat, r.lng], { icon })
				.addTo(map)
				.bindPopup(`
					<div style="font-family:Inter,sans-serif;min-width:140px;">
						<a href="/restaurant/${r.id}" style="font-size:14px;font-weight:700;color:#1A1A1A;text-decoration:none;">${r.name}</a>
						${r.city ? `<br><span style="color:#9A8E7E;font-size:12px;">${r.city}</span>` : ''}
						${pin.rating ? `<br><span style="color:#5D4E3F;font-size:13px;">♥ ${pin.rating}/5</span>` : ''}
						<br><span style="color:#9A8E7E;font-size:11px;">${pin.status === 'visited' ? 'Rated' : 'On the List'}</span>
					</div>
				`);
			markersById.set(r.id, marker);
			allMarkers.push({
				marker,
				cuisineSlug: r.cuisineDetail?.slug || '',
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
					<input
						type="text"
						bind:value={citySearch}
						onkeydown={(e) => e.key === 'Enter' && mapSearch()}
						placeholder={t('search.city') + '...'}
						class="min-w-0 flex-1 rounded-input border border-cream-dark bg-white px-3 py-2 text-base text-ink outline-none focus:border-jade"
					/>
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
						aria-label="Close search"
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
			<span class="inline-block h-2 w-2 rounded-full" style="background:#5D4E3F;"></span>{t('map.yourVisited', { name: authStore.user?.displayName || 'You' })}
		</span>
		<span class="flex items-center gap-1 rounded-full bg-white/90 px-2 py-1 text-[10px] font-medium text-ink shadow-card">
			<span class="inline-block h-2 w-2 rounded-full" style="background:#9A8E7E;"></span>{t('map.yourToVisit', { name: authStore.user?.displayName || 'You' })}
		</span>
		{#if friendCount > 0}
			<span class="flex items-center gap-1 rounded-full bg-white/90 px-2 py-1 text-[10px] font-medium text-ink shadow-card">
				<span class="inline-block h-2 w-2 rounded-full" style="background:#C9A678;"></span>{t('map.friendPins')}
			</span>
		{/if}
	</div>

	<!-- FAB: Add Pin -->
	<button
		aria-label="Add pin"
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
