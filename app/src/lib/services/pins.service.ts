import { api } from './api.service';
import type { Persona, Pin, PinCreate, PaginatedResponse, SharedList, SharedListPublic } from '$lib/types';

export const pinsService = {
	list(params?: { status?: string; persona?: string; city?: string }): Promise<PaginatedResponse<Pin>> {
		const query = new URLSearchParams();
		if (params?.status) query.set('status', params.status);
		if (params?.persona) query.set('persona', params.persona);
		if (params?.city) query.set('city', params.city);
		const qs = query.toString();
		return api.get(`/pins/${qs ? `?${qs}` : ''}`);
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

	personas(): Promise<Persona[]> {
		return api.get('/personas/');
	},

	// Shared lists
	sharedLists(): Promise<SharedList[]> {
		const res = api.get<PaginatedResponse<SharedList> | SharedList[]>('/shared-lists/');
		return res.then((r) => (Array.isArray(r) ? r : r.results));
	},

	createSharedList(data: { title?: string; statusFilter?: string }): Promise<SharedList> {
		return api.post('/shared-lists/', data);
	},

	deleteSharedList(id: number): Promise<void> {
		return api.delete(`/shared-lists/${id}/`);
	},

	getSharedList(token: string): Promise<SharedListPublic> {
		return api.get(`/shared/${token}/`);
	},
};
