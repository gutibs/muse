import { api } from './api.service';

export interface PlaceSuggestion {
	placeId: string;
	name: string;
	address: string;
}

export interface PlaceDetails {
	placeId: string;
	name: string;
	address: string;
	city: string;
	country: string;
	lat: number;
	lng: number;
	website: string;
	phone: string;
	imageUrl: string;
	openingHours: string[];
	type: string;
}

export interface CitySuggestion {
	placeId: string;
	name: string;
	display: string;
}

/** Subset of the Nominatim address dict that LocationPicker actually parses. */
export interface NominatimAddress {
	road?: string;
	house_number?: string;
	city?: string;
	town?: string;
	village?: string;
	municipality?: string;
	country?: string;
	[k: string]: unknown;
}

export interface ReverseGeocodeResult {
	displayName: string | null;
	address: NominatimAddress;
}

export const placesService = {
	autocomplete(query: string, lat?: number, lng?: number): Promise<{ results: PlaceSuggestion[] }> {
		const qs = new URLSearchParams({ q: query });
		if (lat !== undefined) qs.set('lat', String(lat));
		if (lng !== undefined) qs.set('lng', String(lng));
		return api.get(`/places/autocomplete/?${qs}`);
	},

	details(placeId: string): Promise<PlaceDetails> {
		return api.get(`/places/details/${placeId}/`);
	},

	cityAutocomplete(query: string): Promise<{ results: CitySuggestion[] }> {
		return api.get(`/places/cities/autocomplete/?q=${encodeURIComponent(query)}`);
	},

	/**
	 * Reverse geocoding via the backend Nominatim proxy. Direct browser
	 * calls violated Nominatim's usage policy; the backend adds the
	 * required User-Agent and email and applies a per-user rate limit.
	 */
	reverseGeocode(lat: number, lng: number): Promise<ReverseGeocodeResult> {
		return api.get(
			`/places/reverse-geocode/?lat=${encodeURIComponent(lat)}&lng=${encodeURIComponent(lng)}`,
		);
	},
};
