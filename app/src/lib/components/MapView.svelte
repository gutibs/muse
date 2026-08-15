<script lang="ts">
	import { browser } from '$app/environment';
	import { getCurrentPosition } from '$lib/utils/geolocate';
	import { createMap, loadLeaflet } from '$lib/utils/map';
	import type L from 'leaflet';

	let {
		center = [51.505, -0.09] as [number, number],
		zoom = 13,
		autoLocate = true,
		onMapReady,
	}: {
		center?: [number, number];
		zoom?: number;
		autoLocate?: boolean;
		onMapReady?: (map: L.Map) => void;
	} = $props();

	let mapContainer: HTMLDivElement;
	let map: L.Map | null = null;

	$effect(() => {
		if (!browser || !mapContainer || map) return;

		let instance: L.Map | null = null;
		let cancelled = false;

		(async () => {
			const Leaflet = await loadLeaflet();

			// Effect was torn down before Leaflet finished loading
			if (cancelled || !mapContainer) return;

			instance = createMap(Leaflet, mapContainer, { center, zoom });

			let userInteracted = false;
			if (autoLocate) {
				instance.once('dragstart', () => { userInteracted = true; });
				instance.once('zoomstart', () => { userInteracted = true; });
				instance.once('popupopen', () => { userInteracted = true; });
			}

			map = instance;
			onMapReady?.(instance);

			// Geolocate via the Capacitor wrapper instead of Leaflet's locate().
			// On Android, Leaflet's `navigator.geolocation` path hits the WebView
			// permission auto-grant in MainActivity.java but never triggers the
			// Android runtime permission dialog, so location silently fails on a
			// fresh install. Going through `@capacitor/geolocation` invokes
			// requestPermissions() which shows the OS prompt. We run this AFTER
			// onMapReady so listeners attached by the parent page see the
			// synthetic `locationfound` / `locationerror` events.
			if (autoLocate) {
				getCurrentPosition({ enableHighAccuracy: true, timeout: 10000, maximumAge: 60000 })
					.then((pos) => {
						if (cancelled || !instance) return;
						const latlng = Leaflet.latLng(pos.latitude, pos.longitude);
						if (!userInteracted) instance.setView(latlng, 16);
						instance.fire('locationfound', { latlng, accuracy: pos.accuracy });
					})
					.catch((err) => {
						if (cancelled || !instance) return;
						console.warn('[map] geolocation failed:', err);
						instance.fire('locationerror', { message: err?.message ?? String(err) });
					});
			}
		})();

		return () => {
			cancelled = true;
			instance?.remove();
			instance = null;
			map = null;
		};
	});
</script>

<div bind:this={mapContainer} class="h-full w-full"></div>

<style>
	:global(.leaflet-control-attribution) {
		font-size: 10px !important;
		background: rgba(255, 255, 255, 0.7) !important;
		padding: 2px 6px !important;
	}

	:global(.leaflet-control-zoom a) {
		width: 36px !important;
		height: 36px !important;
		line-height: 36px !important;
		font-size: 16px !important;
		border-radius: 10px !important;
		background: white !important;
		color: #1A1A1A !important;
		box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06), 0 1px 2px rgba(0, 0, 0, 0.04) !important;
	}

	:global(.leaflet-control-zoom) {
		border: none !important;
		border-radius: 10px !important;
		overflow: hidden;
		box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06), 0 1px 2px rgba(0, 0, 0, 0.04) !important;
	}
</style>
