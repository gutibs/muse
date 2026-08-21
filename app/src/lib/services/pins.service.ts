import { api } from './api.service';
import type { Pin, PinCreate, PaginatedResponse, SharedList, SharedListPublic } from '$lib/types';

type PinFilters = {
	status?: string;
	tag?: string;
	city?: string;
	favourite?: boolean;
	page?: number;
};

function pinsQuery(params?: PinFilters): string {
	const query = new URLSearchParams();
	if (params?.status) query.set('status', params.status);
	if (params?.tag) query.set('tag', params.tag);
	if (params?.city) query.set('city', params.city);
	if (params?.favourite) query.set('favourite', 'true');
	if (params?.page) query.set('page', String(params.page));
	const qs = query.toString();
	return `/pins/${qs ? `?${qs}` : ''}`;
}

export const pinsService = {
	/** One page (20 rows). Use for infinite scroll, the way the feed does it. */
	list(params?: PinFilters): Promise<PaginatedResponse<Pin>> {
		return api.get(pinsQuery(params));
	},

	/**
	 * Every pin matching the filters, following pagination.
	 *
	 * For screens that need the whole set rather than a page of it: the map
	 * plots all of them, the restaurant screen looks for your pin among all of
	 * them. Both used to read only the first 20.
	 */
	listAll(params?: Omit<PinFilters, 'page'>): Promise<Pin[]> {
		return api.getAll<Pin>(pinsQuery(params));
	},

	get(id: number): Promise<Pin> {
		return api.get(`/pins/${id}/`);
	},

	create(data: PinCreate): Promise<Pin> {
		return api.post('/pins/', data);
	},

	update(id: number, data: Partial<PinCreate>): Promise<Pin> {
		return api.patch(`/pins/${id}/`, data);
	},

	delete(id: number): Promise<void> {
		return api.delete(`/pins/${id}/`);
	},

	/**
	 * Marca o desmarca un favorito.
	 *
	 * Endpoint propio y no un PATCH: el backend lo escribe sin tocar
	 * `updatedAt`, porque la lista se ordena por ese campo y el pin saltaría
	 * al tope apenas tocás la estrella.
	 */
	setFavourite(id: number, isFavourite: boolean): Promise<{ id: number; isFavourite: boolean }> {
		return api.post(`/pins/${id}/favourite/`, { isFavourite });
	},



	// Shared lists
	sharedLists(): Promise<SharedList[]> {
		const res = api.get<PaginatedResponse<SharedList> | SharedList[]>('/shared-lists/');
		return res.then((r) => (Array.isArray(r) ? r : r.results));
	},

	createSharedList(data: {
		title?: string;
		statusFilter?: string;
		kind?: string;
		/** Orden de la lista curada. El orden del array es el de la pantalla. */
		pinIds?: number[];
		expiresAt?: string | null;
	}): Promise<SharedList> {
		return api.post('/shared-lists/', data);
	},

	deleteSharedList(id: number): Promise<void> {
		return api.delete(`/shared-lists/${id}/`);
	},

	getSharedList(token: string): Promise<SharedListPublic> {
		return api.get(`/shared/${token}/`);
	},
};
