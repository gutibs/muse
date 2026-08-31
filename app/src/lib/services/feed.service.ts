import { api } from './api.service';
import type { Activity, PaginatedResponse } from '$lib/types';

export const feedService = {
	/** `insiderOnly` deja sólo la actividad de gente verificada. Acota, nunca
	 * amplía: el backend lo aplica sobre lo que ya podés ver. */
	list(page = 1, insiderOnly = false): Promise<PaginatedResponse<Activity>> {
		const query = new URLSearchParams({ page: String(page) });
		// El booleano se emite sólo cuando es true, como en pins.service.
		if (insiderOnly) query.set('insider', 'true');
		return api.get(`/feed/?${query.toString()}`);
	},
};
