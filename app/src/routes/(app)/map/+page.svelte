<script lang="ts">
	import { browser } from '$app/environment';
	import { goto } from '$app/navigation';
	import MapView from '$lib/components/MapView.svelte';
	import { pinsService } from '$lib/services/pins.service';
	import type { Pin } from '$lib/types';
	import type L from 'leaflet';

	let pins = $state<Pin[]>([]);

	async function loadPins() {
		try {
			const res = await pinsService.list();
			pins = res.results;
		} catch {
			// silent fail — empty map
		}
	}

	async function onMapReady(map: L.Map) {
		await loadPins();
		if (!browser || pins.length === 0) return;

		const leaflet = await import('leaflet');
		const L = leaflet.default;

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

			L.marker([r.lat, r.lng], { icon })
				.addTo(map)
				.bindPopup(`
					<div style="font-family:Inter,sans-serif;min-width:140px;">
						<strong style="font-size:14px;">${r.name}</strong>
						${r.city ? `<br><span style="color:#8A8A8A;font-size:12px;">${r.city}</span>` : ''}
						${pin.rating ? `<br><span style="color:#2D6A4F;font-size:13px;">★ ${pin.rating}/5</span>` : ''}
						<br><span style="color:#8A8A8A;font-size:11px;">${pin.status === 'visited' ? 'Visited' : 'To Visit'}</span>
					</div>
				`);
		}
	}
</script>

<div class="relative h-full w-full">
	<MapView center={[51.505, -0.09]} zoom={3} {onMapReady} />

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
