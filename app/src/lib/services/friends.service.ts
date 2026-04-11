import { api } from './api.service';
import type { Friendship, PublicUser } from '$lib/types';

export const friendsService = {
	list(): Promise<Friendship[]> {
		return api.get('/auth/friendships/friends/');
	},

	requests(): Promise<Friendship[]> {
		return api.get('/auth/friendships/requests/');
	},

	sendRequest(toUserId: number): Promise<Friendship> {
		return api.post('/auth/friendships/', { toUserId });
	},

	respond(id: number, status: 'accepted' | 'declined'): Promise<Friendship> {
		return api.patch(`/auth/friendships/${id}/`, { status });
	},

	remove(id: number): Promise<void> {
		return api.delete(`/auth/friendships/${id}/`);
	},

	inviteByEmail(email: string): Promise<void> {
		return api.post('/auth/invite/', { email });
	},

	search(query: string): Promise<PublicUser[]> {
		return api.get(`/auth/search/?q=${encodeURIComponent(query)}`);
	},
};
