import { googleImportErrorKey } from '$lib/services/google-import';
import type { PlaceSuggestion } from '$lib/services/places.service';
import { logSilent } from './logger';

export interface GoogleSuggestionsState {
	results: PlaceSuggestion[];
	failed: boolean;
	messageKey: string | null;
}

export function readGoogleSuggestions(
	settled: PromiseSettledResult<{ results: PlaceSuggestion[] }>,
	scope: string,
): GoogleSuggestionsState {
	if (settled.status === 'rejected') {
		logSilent(scope, settled.reason);
		return { results: [], failed: true, messageKey: googleImportErrorKey(settled.reason) };
	}
	return { results: settled.value.results, failed: false, messageKey: null };
}
