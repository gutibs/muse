<script lang="ts">
	import { browser } from '$app/environment';
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import MapView from '$lib/components/MapView.svelte';
	import { pinsService } from '$lib/services/pins.service';
	import { restaurantsService } from '$lib/services/restaurants.service';
	import type { Pin, Restaurant } from '$lib/types';
	import type L from 'leaflet';

	let hasFocus = $derived(Boolean(page.url.searchParams.get('focus')));

	async function loadAllRestaurants(): Promise<Restaurant[]> {
		const all: Restaurant[] = [];
		let page = 1;
		while (true) {
			const res = await restaurantsService.list({ page });
			all.push(...res.results);
			if (!res.next) break;
			page += 1;
			if (page > 50) break; // safety cap
		}
		return all;
	}

	async function onMapReady(map: L.Map) {
		if (!browser) return;

		const [pinsRes, restaurants] = await Promise.all([
			pinsService.list().catch(() => ({ results: [] as Pin[] })),
			loadAllRestaurants().catch(() => [] as Restaurant[]),
		]);

		const pins = pinsRes.results;
		const pinnedRestaurantIds = new Set(pins.map((p) => p.restaurant));

		const leaflet = await import('leaflet');
		const L = leaflet.default;

		// Track markers by restaurant id to focus from query param
		const markersById = new Map<number, L.Marker>();

		// 1. Render unpinned restaurants as small neutral markers
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
						<strong style="font-size:14px;">${r.name}</strong>
						${r.city ? `<br><span style="color:#8A8A8A;font-size:12px;">${r.city}</span>` : ''}
						${r.cuisineDetail ? `<br><span style="color:#8A8A8A;font-size:11px;">${r.cuisineDetail.name}</span>` : ''}
						${r.averageRating ? `<br><span style="color:#2D6A4F;font-size:13px;">★ ${r.averageRating.toFixed(1)}</span>` : ''}
					</div>
				`);
			markersById.set(r.id, marker);
		}

		// 2. Render user pins on top with bigger colored markers
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
						<strong style="font-size:14px;">${r.name}</strong>
						${r.city ? `<br><span style="color:#8A8A8A;font-size:12px;">${r.city}</span>` : ''}
						${pin.rating ? `<br><span style="color:#2D6A4F;font-size:13px;">★ ${pin.rating}/5</span>` : ''}
						<br><span style="color:#8A8A8A;font-size:11px;">${pin.status === 'visited' ? 'Visited' : 'To Visit'}</span>
					</div>
				`);
			markersById.set(r.id, marker);
		}

		// Focus a specific restaurant if ?focus=<id> is in URL
		const focusId = Number(page.url.searchParams.get('focus'));
		if (focusId) {
			const target = markersById.get(focusId);
			if (target) {
				map.setView(target.getLatLng(), 15, { animate: true });
				target.openPopup();
			}
		}
	}
</script>

<div class="relative h-full w-full">
	<MapView center={[51.505, -0.09]} zoom={3} autoLocate={!hasFocus} {onMapReady} />

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
