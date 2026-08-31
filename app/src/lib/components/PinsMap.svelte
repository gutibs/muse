<script lang="ts">
	import { browser } from '$app/environment';
	import type { Pin, Restaurant } from '$lib/types';
	import { dietaryBadgesHtml } from '$lib/utils/dietary-badges';
	import { createMap, createPinIcon, loadLeaflet, PIN_COLORS } from '$lib/utils/map';
	import { buildRestaurantPopup, ownerFromUser, type PopupOwner } from '$lib/utils/map-popup';
	import type L from 'leaflet';

	/**
	 * Map item: usually a `Pin`, but search results pass restaurant-only items
	 * (no pin, just averageRating). Both shapes are handled by `popupFor`.
	 *
	 * Typed as what the map actually reads rather than as the full `Pin` and
	 * `Restaurant`. The share page renders the same markers from the narrower
	 * anonymous payload (see pins/serializers_public.py), and demanding the
	 * full types there would mean inventing fields the backend deliberately
	 * withholds.
	 */
	export type MapRestaurant = Pick<Restaurant, 'id' | 'name' | 'city' | 'lat' | 'lng'> &
		Partial<Pick<Restaurant, 'averageRating' | 'cuisinesDetail' | 'tagsDetail'>>;

	export type MapPin = Pick<Pin, 'rating' | 'status'> & { restaurantDetail: MapRestaurant };

	export type MapItem =
		| { kind: 'pin'; pin: MapPin; owner?: PopupOwner | null }
		| { kind: 'restaurant'; restaurant: MapRestaurant };

	/**
	 * `accent` accepts either a fixed color name or a per-item function. The
	 * function form is what the audit needed for friend-vs-own pin styling
	 * (option a from the spec).
	 */
	type AccentInput = keyof typeof PIN_COLORS | ((item: MapItem) => keyof typeof PIN_COLORS);

	interface Props {
		items: MapItem[];
		/** Color name from PIN_COLORS, or function (item) => color name. */
		accent?: AccentInput;
		/** Wrap restaurant name in `<a href="/restaurant/${id}">`. */
		link?: boolean;
		/** Append dietary badges built from `restaurant.tagsDetail`. */
		showDietary?: boolean;
		/** i18n-resolved label per item, e.g. (item) => t('map.popupRated'). */
		statusLabelFor?: (item: MapItem) => string | undefined;
		/** Click handler on a marker. The map fitBounds still runs as usual. */
		onItemClick?: (item: MapItem) => void;
		/** Browser geolocation on first load (off by default). */
		autoLocate?: boolean;
		/** Override fitBounds padding/maxZoom. */
		fitOptions?: L.FitBoundsOptions;
	}

	let {
		items,
		accent = 'visited',
		link = false,
		showDietary = false,
		statusLabelFor,
		onItemClick,
		autoLocate = false,
		// 24 y no 40: el padding se descuenta del ancho útil, y en un teléfono
		// de 390px esos 32px de más eran la diferencia entre encuadrar una
		// lista de dos continentes y dejar uno afuera.
		fitOptions = { padding: [24, 24], maxZoom: 14 },
	}: Props = $props();

	let mapContainer = $state<HTMLDivElement | undefined>(undefined);
	let mapInstance: L.Map | null = null;
	let markersLayer: L.LayerGroup | null = null;
	let Leaflet: typeof L | null = null;
	let bootError = $state(false);

	function colorFor(item: MapItem): string {
		const key = typeof accent === 'function' ? accent(item) : accent;
		return PIN_COLORS[key];
	}

	function coordsFor(
		item: MapItem
	): { lat: number; lng: number; restaurant: MapRestaurant } | null {
		const restaurant = item.kind === 'pin' ? item.pin.restaurantDetail : item.restaurant;
		if (!restaurant?.lat || !restaurant?.lng) return null;
		return { lat: restaurant.lat, lng: restaurant.lng, restaurant };
	}

	function popupFor(item: MapItem, restaurant: MapRestaurant): string {
		const dietaryHtml = showDietary ? dietaryBadgesHtml(restaurant.tagsDetail) : undefined;
		const statusLabel = statusLabelFor?.(item);
		if (item.kind === 'pin') {
			return buildRestaurantPopup({
				restaurant,
				pin: item.pin,
				owner: item.owner ?? null,
				link,
				statusLabel,
				dietaryHtml,
			});
		}
		// restaurant-only items: average rating, no pin context
		return buildRestaurantPopup({
			restaurant,
			link,
			showCuisines: true,
			statusLabel,
			dietaryHtml,
		});
	}

	function renderMarkers() {
		if (!mapInstance || !markersLayer || !Leaflet) return;
		markersLayer.clearLayers();

		const positions: [number, number][] = [];
		for (const item of items) {
			const coords = coordsFor(item);
			if (!coords) continue;

			const marker = Leaflet.marker([coords.lat, coords.lng], {
				icon: createPinIcon(Leaflet, colorFor(item)),
			});
			marker.bindPopup(popupFor(item, coords.restaurant));
			if (onItemClick) marker.on('click', () => onItemClick(item));
			marker.addTo(markersLayer);
			positions.push([coords.lat, coords.lng]);
		}

		if (positions.length === 0) return;

		// El encuadre se calcula contra el tamaño del contenedor, y en el
		// primer render ese tamaño todavía no existe: el div se acaba de
		// insertar y el layout no corrió. Leaflet encuadra entonces sobre un
		// viewport de cero y los markers terminan fuera de la vista — el mapa
		// de una lista compartida se abría en Asia Central con sus tres
		// restaurantes afuera, y la mitad de las tiles sin pedir.
		//
		// `invalidateSize` le dice a Leaflet que vuelva a medir antes de
		// encuadrar; el timeout deja que el layout corra primero.
		//
		// `setTimeout` y NO `requestAnimationFrame`: el navegador no dispara
		// rAF en una pestaña que no está visible, así que el encuadre no
		// ocurría nunca y el mapa se quedaba en su vista inicial —el centro
		// del mundo— con los markers donde cayeran. Un timeout corre igual.
		const fit = () => {
			if (!mapInstance) return;
			mapInstance.invalidateSize();
			mapInstance.fitBounds(positions, fitOptions);
		};
		setTimeout(fit, 0);
	}

	$effect(() => {
		if (!browser || !mapContainer || mapInstance) return;

		let cancelled = false;
		(async () => {
			try {
				Leaflet = await loadLeaflet();
				if (cancelled || !mapContainer) return;

				mapInstance = createMap(Leaflet, mapContainer);

				markersLayer = Leaflet.layerGroup().addTo(mapInstance);
				renderMarkers();

				if (autoLocate) {
					mapInstance.locate({
						setView: false,
						enableHighAccuracy: true,
						timeout: 10000,
						maximumAge: 60000,
					});
					mapInstance.once('locationfound', (e: L.LocationEvent) => {
						mapInstance?.setView(e.latlng, 14);
					});
					mapInstance.once('locationerror', (e: L.ErrorEvent) => {
						console.warn('[PinsMap] geolocation failed:', e.message);
					});
				}
			} catch (err) {
				console.warn('[PinsMap] Leaflet bootstrap failed:', err);
				bootError = true;
			}
		})();

		return () => {
			cancelled = true;
			mapInstance?.remove();
			mapInstance = null;
			markersLayer = null;
		};
	});

	// Re-render when items change. Touch length so the effect tracks.
	$effect(() => {
		void items.length;
		if (mapInstance && markersLayer && Leaflet) renderMarkers();
	});

	// Suppress unused warning when caller uses ownerFromUser elsewhere.
	void ownerFromUser;
</script>

{#if bootError}
	<div class="flex h-full w-full items-center justify-center bg-stone-100 p-6 text-center text-sm text-stone-500">
		Map could not be loaded.
	</div>
{:else}
	<div bind:this={mapContainer} class="h-full w-full"></div>
{/if}

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
		color: #1a1a1a !important;
		box-shadow:
			0 1px 3px rgba(0, 0, 0, 0.06),
			0 1px 2px rgba(0, 0, 0, 0.04) !important;
	}

	:global(.leaflet-control-zoom) {
		border: none !important;
		border-radius: 10px !important;
		overflow: hidden;
		box-shadow:
			0 1px 3px rgba(0, 0, 0, 0.06),
			0 1px 2px rgba(0, 0, 0, 0.04) !important;
	}
</style>
