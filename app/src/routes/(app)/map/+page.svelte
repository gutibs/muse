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
	import { dietaryBadgesHtml } from '$lib/utils/dietary-badges';
	import type L from 'leaflet';

	let hasFocus = $derived(Boolean(page.url.searchParams.get('focus')));
	let showLegend = $state(false);
	let showFriendPins = $state(false);
	let friendLayers = $state<L.LayerGroup | null>(null);
	let mapRef = $state<L.Map | null>(null);
	let friendCount = $state(0);

	async function loadAllRestaurants(): Promise<Restaurant[]> {
		const all: Restaurant[] = [];
		let pg = 1;
		while (true) {
			const res = await restaurantsService.list({ page: pg });
			all.push(...res.results);
			if (!res.next) break;
			pg += 1;
			if (pg > 50) break;
		}
		return all;
	}

	function getOtherUser(f: Friendship, myId: number): PublicUser {
		return f.fromUser.id === myId ? f.toUser : f.fromUser;
	}

	async function loadFriendPins(map: L.Map, Leaflet: typeof L) {
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
							html: `<div style="width:22px;height:22px;background:#D4A373;border:3px solid white;border-radius:50%;box-shadow:0 2px 6px rgba(0,0,0,0.2);"></div>`,
							iconSize: [22, 22],
							iconAnchor: [11, 11],
						});

						Leaflet.marker([r.lat, r.lng], { icon })
							.addTo(group)
							.bindPopup(`
								<div style="font-family:Inter,sans-serif;min-width:140px;">
									<span style="color:#D4A373;font-size:11px;font-weight:600;">${other.displayName || other.email}</span>
									<br><a href="/restaurant/${r.id}" style="font-size:14px;font-weight:700;color:#1A1A1A;text-decoration:none;">${r.name}</a>
									${r.city ? `<br><span style="color:#8A8A8A;font-size:12px;">${r.city}</span>` : ''}
									${pin.rating ? `<br><span style="color:#2D6A4F;font-size:13px;">★ ${pin.rating}/5</span>` : ''}
								</div>
							`);
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

		const [pinsRes, restaurants] = await Promise.all([
			pinsService.list().catch(() => ({ results: [] as Pin[] })),
			loadAllRestaurants().catch(() => [] as Restaurant[]),
		]);

		const pins = pinsRes.results;
		const pinnedRestaurantIds = new Set(pins.map((p) => p.restaurant));

		const leaflet = await import('leaflet');
		const L = leaflet.default;

		const markersById = new Map<number, L.Marker>();

		for (const r of restaurants) {
			if (!r.lat || !r.lng) continue;
			if (pinnedRestaurantIds.has(r.id)) continue;

			const icon = L.divIcon({
				className: '',
				html: `<div style="width:14px;height:14px;background:#C9B7A0;border:2px solid white;border-radius:50%;box-shadow:0 1px 3px rgba(0,0,0,0.2);"></div>`,
				iconSize: [14, 14],
				iconAnchor: [7, 7],
			});

			const marker = L.marker([r.lat, r.lng], { icon })
				.addTo(map)
				.bindPopup(`
					<div style="font-family:Inter,sans-serif;min-width:140px;">
						<a href="/restaurant/${r.id}" style="font-size:14px;font-weight:700;color:#1A1A1A;text-decoration:none;">${r.name}</a>
						${r.city ? `<br><span style="color:#8A8A8A;font-size:12px;">${r.city}</span>` : ''}
						${r.cuisineDetail ? `<br><span style="color:#8A8A8A;font-size:11px;">${r.cuisineDetail.name}</span>` : ''}
						${r.averageRating ? `<br><span style="color:#2D6A4F;font-size:13px;">★ ${r.averageRating.toFixed(1)}</span>` : ''}
						${dietaryBadgesHtml(r.tagsDetail)}
					</div>
				`);
			markersById.set(r.id, marker);
		}

		for (const pin of pins) {
			const r = pin.restaurantDetail;
			if (!r?.lat || !r?.lng) continue;

			const color = pin.status === 'visited' ? '#2D6A4F' : '#8A8A8A';
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
						${r.city ? `<br><span style="color:#8A8A8A;font-size:12px;">${r.city}</span>` : ''}
						${pin.rating ? `<br><span style="color:#2D6A4F;font-size:13px;">★ ${pin.rating}/5</span>` : ''}
						<br><span style="color:#8A8A8A;font-size:11px;">${pin.status === 'visited' ? 'Visited' : 'To Visit'}</span>
					</div>
				`);
			markersById.set(r.id, marker);
		}

		const focusId = Number(page.url.searchParams.get('focus'));
		if (focusId) {
			const target = markersById.get(focusId);
			if (target) {
				map.setView(target.getLatLng(), 15, { animate: true });
				target.openPopup();
			}
		}

		loadFriendPins(map, L);
	}
</script>

<div class="relative h-full w-full">
	<MapView center={[51.505, -0.09]} zoom={3} autoLocate={!hasFocus} {onMapReady} />

	<!-- Top controls -->
	<div class="absolute left-4 top-4 z-1000 flex flex-col gap-2">
		<!-- Friend pins toggle -->
		{#if friendCount > 0}
			<button
				onclick={toggleFriendPins}
				class="flex items-center gap-2 rounded-full px-3 py-2 text-xs font-medium shadow-elevated active:scale-95
					{showFriendPins ? 'bg-amber-700 text-white' : 'bg-white text-ink'}"
			>
				<div
					class="h-3 w-3 rounded-full border-2 border-white"
					style="background: #D4A373;"
				></div>
				{showFriendPins ? t('map.friendsOn') : t('map.friendsOff')}
			</button>
		{/if}

		<!-- Legend toggle -->
		<button
			onclick={() => (showLegend = !showLegend)}
			class="flex h-9 w-9 items-center justify-center rounded-full bg-white text-ink-muted shadow-elevated active:scale-95"
			aria-label="Toggle legend"
		>
			<svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
				<circle cx="12" cy="12" r="10" />
				<path d="M12 16v-4M12 8h.01" />
			</svg>
		</button>
	</div>

	<!-- Legend -->
	{#if showLegend}
		<div class="absolute left-4 top-24 z-1000 rounded-card bg-white p-3 shadow-elevated">
			<div class="space-y-2 text-xs">
				<div class="flex items-center gap-2">
					<div class="h-4 w-4 rounded-full border-2 border-white shadow-card" style="background:#2D6A4F;"></div>
					<span class="text-ink">{t('map.yourVisited')}</span>
				</div>
				<div class="flex items-center gap-2">
					<div class="h-4 w-4 rounded-full border-2 border-white shadow-card" style="background:#8A8A8A;"></div>
					<span class="text-ink">{t('map.yourToVisit')}</span>
				</div>
				{#if friendCount > 0}
					<div class="flex items-center gap-2">
						<div class="h-3.5 w-3.5 rounded-full border-2 border-white shadow-card" style="background:#D4A373;"></div>
						<span class="text-ink">{t('map.friendPins')}</span>
					</div>
				{/if}
				<div class="flex items-center gap-2">
					<div class="h-2.5 w-2.5 rounded-full border-2 border-white shadow-card" style="background:#C9B7A0;"></div>
					<span class="text-ink">{t('map.restaurants')}</span>
				</div>
			</div>
		</div>
	{/if}

	<!-- FAB: Add Pin -->
	<button
		aria-label="Add pin"
		onclick={() => goto('/pin/new')}
		class="absolute bottom-4 right-4 z-1000 flex h-14 w-14 items-center justify-center rounded-full bg-jade text-white shadow-elevated active:scale-95"
	>
		<svg class="h-7 w-7" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
			<line x1="12" y1="5" x2="12" y2="19" />
			<line x1="5" y1="12" x2="19" y2="12" />
		</svg>
	</button>
</div>
