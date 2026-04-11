import { api } from './api.service';
import type { Pin, Profile } from '$lib/types';

export const usersService = {
	getProfile(userId: number): Promise<Profile> {
		return api.get(`/auth/users/${userId}/`);
	},

	getPins(userId: number, status?: 'visited' | 'to_visit'): Promise<Pin[]> {
		const qs = status ? `?status=${status}` : '';
		return api.get(`/auth/users/${userId}/pins/${qs}`);
	},
};
