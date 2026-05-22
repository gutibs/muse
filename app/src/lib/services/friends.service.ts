import { api } from './api.service';
import { i18n } from '$lib/i18n/index.svelte';
import type { Friendship, PaginatedResponse, PublicUser } from '$lib/types';

export type EmailInvitation = {
	id: number;
	email: string;
	accepted: boolean;
	createdAt: string;
};

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
		// Pass the sender's UI language so the backend can localise the email.
		return api.post('/auth/invite/', { email, language: i18n.locale });
	},

	async sentInvitations(): Promise<EmailInvitation[]> {
		const res = await api.get<PaginatedResponse<EmailInvitation> | EmailInvitation[]>(
			'/auth/invite/'
		);
		return Array.isArray(res) ? res : res.results;
	},

	async search(query: string): Promise<PublicUser[]> {
		const res = await api.get<PaginatedResponse<PublicUser> | PublicUser[]>(
			`/auth/search/?q=${encodeURIComponent(query)}`
		);
		return Array.isArray(res) ? res : res.results;
	},
};
