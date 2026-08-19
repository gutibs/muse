import { ApiError, type Restaurant } from '$lib/types';
import { restaurantsService } from './restaurants.service';

/**
 * Import a Google place into our catalogue and return the Restaurant row.
 *
 * Two screens had their own transcription of this flow and had already
 * drifted — the search screen handled 429 and the pin screen did not, so the
 * same rate limit produced a helpful message in one place and a generic
 * "couldn't import" in the other.
 *
 * The old flow also called `placesService.details()` first and forwarded
 * eleven fields to the backend, which reads only `placeId` and re-fetches
 * everything from Google itself. That made every import cost two billable
 * Place Details calls instead of one — and if the restaurant was already in
 * our database, the backend returned before calling Google at all, so the
 * client's details call was pure waste.
 */
export function importPlace(placeId: string): Promise<Restaurant> {
	return restaurantsService.fromGoogle(placeId);
}

/**
 * i18n key for a Google-import failure, or null when the caller should use
 * its own fallback message.
 *
 * Returns the key rather than the text so the mapping lives in one place
 * while each screen keeps its own wording for the generic case.
 */
export function googleImportErrorKey(err: unknown): string | null {
	if (!(err instanceof ApiError)) return 'common.networkError';
	switch (err.status) {
		case 503:
			return 'pin.googleNotConfigured';
		case 502:
			return 'pin.googleUnavailable';
		case 429:
			return 'search.tooManyRequests';
		default:
			return null;
	}
}
