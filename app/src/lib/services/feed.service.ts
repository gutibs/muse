import { api } from './api.service';
import type { Activity, PaginatedResponse } from '$lib/types';

export const feedService = {
	list(page = 1): Promise<PaginatedResponse<Activity>> {
		return api.get(`/feed/?page=${page}`);
	},
};
