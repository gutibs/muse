import { api } from './api.service';
import type { Cuisine, Tag, Restaurant, RestaurantCreate, RestaurantDetail, PaginatedResponse } from '$lib/types';

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

	nearby(lat: number, lng: number, radius = 5): Promise<Restaurant[]> {
		return api.get(`/restaurants/nearby/?lat=${lat}&lng=${lng}&radius=${radius}`);
	},

	cuisines(): Promise<Cuisine[]> {
		return api.get('/cuisines/');
	},

	tags(): Promise<Tag[]> {
		return api.get('/tags/');
	},

	mySuggestions(): Promise<Restaurant[]> {
		return api.get('/restaurants/my_suggestions/');
	},
};
