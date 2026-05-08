<script lang="ts">
	import { browser } from '$app/environment';
	import { t } from '$lib/i18n/index.svelte';
	import type L from 'leaflet';

	let {
		lat = $bindable<number | null>(null),
		lng = $bindable<number | null>(null),
		address = $bindable(''),
		city = $bindable(''),
		country = $bindable(''),
	}: {
		lat: number | null;
		lng: number | null;
		address: string;
		city: string;
		country: string;
	} = $props();

	let mapContainer: HTMLDivElement;
	let map: L.Map | null = null;
	let marker: L.Marker | null = null;
	let geocoding = $state(false);
	let geolocating = $state(false);
	let geoError = $state('');

	async function reverseGeocode(latitude: number, longitude: number) {
		geocoding = true;
		try {
			const res = await fetch(
				`https://nominatim.openstreetmap.org/reverse?lat=${latitude}&lon=${longitude}&format=json&addressdetails=1`,
				{ headers: { 'Accept-Language': 'en' } },
			);
			const data = await res.json();
			if (data.address) {
				const a = data.address;
				const parts = [a.road, a.house_number].filter(Boolean);
				address = parts.join(' ') || data.display_name?.split(',').slice(0, 2).join(',') || '';
				city = a.city || a.town || a.village || a.municipality || '';
				country = a.country || '';
			}
		} catch {
			// silent — user can fill manually
		}
		geocoding = false;
	}

	function geolocate() {
		if (!navigator.geolocation) {
			geoError = t('location.notAvailable');
			return;
		}
		geolocating = true;
		geoError = '';
		navigator.geolocation.getCurrentPosition(
			(pos) => {
				lat = pos.coords.latitude;
				lng = pos.coords.longitude;
				if (map && marker) {
					const latlng = { lat: lat!, lng: lng! } as L.LatLngExpression;
					marker.setLatLng(latlng);
					map.setView(latlng, 16);
				}
				reverseGeocode(lat!, lng!);
				geolocating = false;
			},
			(err) => {
				console.warn('[geolocation]', err.code, err.message);
				geolocating = false;
				if (err.code === err.PERMISSION_DENIED) {
					geoError = t('location.permissionDenied');
				} else if (err.code === err.TIMEOUT) {
					geoError = t('location.timeout');
				} else if (err.code === err.POSITION_UNAVAILABLE) {
					geoError = t('location.unavailable');
				} else {
					geoError = t('location.cantGet');
				}
			},
			{ enableHighAccuracy: true, timeout: 10000, maximumAge: 60000 },
		);
	}

	$effect(() => {
		if (!browser || !mapContainer || map) return;

		let instance: L.Map;

		import('leaflet').then((leaflet) => {
			import('leaflet/dist/leaflet.css');
			const Leaflet = leaflet.default;

			const defaultCenter: [number, number] = lat && lng ? [lat, lng] : [51.505, -0.09];
			const defaultZoom = lat && lng ? 16 : 3;

			instance = Leaflet.map(mapContainer, {
				zoomControl: false,
				attributionControl: false,
			}).setView(defaultCenter, defaultZoom);

			Leaflet.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', {
				maxZoom: 19,
			}).addTo(instance);

			const icon = Leaflet.divIcon({
				className: '',
				html: '<div style="width:32px;height:32px;background:#8A7363;border:3px solid white;border-radius:50%;box-shadow:0 2px 8px rgba(0,0,0,0.3);cursor:grab;"></div>',
				iconSize: [32, 32],
				iconAnchor: [16, 16],
			});

			marker = Leaflet.marker(defaultCenter, { icon, draggable: true }).addTo(instance);

			marker.on('dragend', () => {
				const pos = marker!.getLatLng();
				lat = pos.lat;
				lng = pos.lng;
				reverseGeocode(pos.lat, pos.lng);
			});

			instance.on('click', (e: L.LeafletMouseEvent) => {
				lat = e.latlng.lat;
				lng = e.latlng.lng;
				marker!.setLatLng(e.latlng);
				reverseGeocode(e.latlng.lat, e.latlng.lng);
			});

			map = instance;

			if (!lat || !lng) {
				geolocate();
			}
		});

		return () => {
			instance?.remove();
			map = null;
			marker = null;
		};
	});
</script>

<div class="space-y-3">
	<div class="flex items-center justify-between">
		<span class="text-sm font-medium text-ink-light">{t('location.title')}</span>
		<button
			type="button"
			onclick={geolocate}
			disabled={geolocating}
			class="text-xs font-medium text-jade active:opacity-70"
		>
			{geolocating ? t('location.locating') : t('location.useMyLocation')}
		</button>
	</div>
	{#if geoError}
		<p class="text-xs text-blush">{geoError}</p>
	{/if}

	<div
		bind:this={mapContainer}
		class="h-48 w-full overflow-hidden rounded-card border border-cream-dark"
	></div>

	{#if geocoding}
		<p class="text-xs text-ink-muted">{t('location.lookingUp')}</p>
	{/if}

	<p class="text-xs text-ink-muted">{t('location.tapMap')}</p>
</div>
