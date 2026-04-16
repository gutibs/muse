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
};
