<script lang="ts">
	import { browser } from '$app/environment';
	import type L from 'leaflet';

	let {
		center = [51.505, -0.09] as [number, number],
		zoom = 13,
		onMapReady,
	}: {
		center?: [number, number];
		zoom?: number;
		onMapReady?: (map: L.Map) => void;
	} = $props();

	let mapContainer: HTMLDivElement;
	let map: L.Map | null = null;

	$effect(() => {
		if (!browser || !mapContainer || map) return;

		let instance: L.Map;

		import('leaflet').then((leaflet) => {
			import('leaflet/dist/leaflet.css');

			const Leaflet = leaflet.default;

			instance = Leaflet.map(mapContainer, {
				zoomControl: false,
				attributionControl: false,
				minZoom: 3,
				maxBoundsViscosity: 1.0,
				maxBounds: [[-85, -180], [85, 180]],
			}).setView(center, zoom);

			Leaflet.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', {
				maxZoom: 19,
				noWrap: true,
			}).addTo(instance);

			Leaflet.control.attribution({ position: 'bottomleft', prefix: false })
				.addAttribution('&copy; <a href="https://carto.com/">CARTO</a> &copy; <a href="https://www.openstreetmap.org/copyright">OSM</a>')
				.addTo(instance);

			Leaflet.control.zoom({ position: 'bottomright' }).addTo(instance);

			// Try to geolocate user
			instance.locate({ setView: true, maxZoom: 14 });

			map = instance;
			onMapReady?.(instance);
		});

		return () => {
			instance?.remove();
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
