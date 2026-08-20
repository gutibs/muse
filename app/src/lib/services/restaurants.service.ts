import { api } from './api.service';
import type { Cuisine, Tag, TagKind, Restaurant, RestaurantCreate, RestaurantDetail, PaginatedResponse } from '$lib/types';

export const restaurantsService = {
	list(params?: { search?: string; city?: string; cuisine?: string; page?: number }): Promise<PaginatedResponse<Restaurant>> {
		const query = new URLSearchParams();
		if (params?.search) query.set('search', params.search);
		if (params?.city) query.set('city', params.city);
		if (params?.cuisine) query.set('cuisine', params.cuisine);
		if (params?.page) query.set('page', String(params.page));
		const qs = query.toString();
		return api.get(`/restaurants/${qs ? `?${qs}` : ''}`);
	},

	get(id: number): Promise<RestaurantDetail> {
		return api.get(`/restaurants/${id}/`);
	},

	create(data: RestaurantCreate): Promise<Restaurant> {
		return api.post('/restaurants/', data);
	},

	/**
	 * `placeId` is the only thing the backend reads — it re-fetches every field
	 * from Google itself so a client cannot spoof name/address/coords and skip
	 * admin approval. Typed accordingly: callers used to build an 11-field
	 * payload that was discarded server-side.
	 *
	 * Prefer `importPlace` from `$lib/services/google-import` over calling this
	 * directly; it carries the error mapping.
	 */
	fromGoogle(placeId: string): Promise<Restaurant> {
		return api.post('/restaurants/from_google/', { placeId });
	},

	nearby(lat: number, lng: number, radius = 5): Promise<Restaurant[]> {
		return api.get(`/restaurants/nearby/?lat=${lat}&lng=${lng}&radius=${radius}`);
	},

	cuisines(): Promise<Cuisine[]> {
		return api.get('/cuisines/');
	},

	/**
	 * Catálogo de etiquetas. Sin `kind` vienen todas, incluidas las dietary
	 * y las de sistema — que es por lo que la pantalla de vibe llegó a
	 * ofrecer `vegetarian` y `gluten-free`.
	 */
	tags(kind?: TagKind): Promise<Tag[]> {
		return api.get(kind ? `/tags/?kind=${kind}` : '/tags/');
	},
};
