import { afterEach, describe, expect, it, vi } from 'vitest';
import { api } from './api.service';
import { pinsService } from './pins.service';

describe('pinsService — listas compartidas', () => {
	afterEach(() => vi.restoreAllMocks());

	it('prende la votación con un PATCH sobre la lista', async () => {
		const spy = vi.spyOn(api, 'patch').mockResolvedValue({} as never);

		await pinsService.updateSharedList(7, { votingEnabled: true });

		expect(spy).toHaveBeenCalledWith('/shared-lists/7/', { votingEnabled: true });
	});
});
