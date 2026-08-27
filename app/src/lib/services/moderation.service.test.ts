import { beforeEach, describe, expect, it, vi } from 'vitest';
import { api } from './api.service';
import { moderationService } from './moderation.service';

vi.mock('./api.service', () => ({
	api: { get: vi.fn(), post: vi.fn(), delete: vi.fn() }
}));

describe('moderationService', () => {
	beforeEach(() => {
		vi.mocked(api.post).mockReset().mockResolvedValue({});
		vi.mocked(api.get).mockReset().mockResolvedValue([]);
		vi.mocked(api.delete).mockReset().mockResolvedValue(undefined);
	});

	it('blocks a user by id', async () => {
		await moderationService.block(42);

		expect(api.post).toHaveBeenCalledWith('/auth/blocks/', { userId: 42 });
	});

	it('unblocks by the user id, not by the block id', async () => {
		// El endpoint se direcciona por la persona: quien desbloquea la conoce
		// a ella, no el número de su fila de bloqueo.
		await moderationService.unblock(42);

		expect(api.delete).toHaveBeenCalledWith('/auth/blocks/42/');
	});

	it('lists the blocks I made', async () => {
		await moderationService.blocks();

		expect(api.get).toHaveBeenCalledWith('/auth/blocks/');
	});

	it('reports a user without a pin', async () => {
		await moderationService.report({ reportedUserId: 7, reason: 'harassment' });

		expect(api.post).toHaveBeenCalledWith('/auth/reports/', {
			reportedUserId: 7,
			reason: 'harassment'
		});
	});

	it('reports a review with its pin and detail', async () => {
		await moderationService.report({
			reportedUserId: 7,
			pinId: 99,
			reason: 'inappropriate',
			detail: 'texto ofensivo'
		});

		expect(api.post).toHaveBeenCalledWith('/auth/reports/', {
			reportedUserId: 7,
			pinId: 99,
			reason: 'inappropriate',
			detail: 'texto ofensivo'
		});
	});

	it('omits the optional fields instead of sending them empty', async () => {
		// Mandar pinId: undefined haría que el backend intente resolver un pin
		// nulo; el serializer lo acepta como ausente, no como null.
		await moderationService.report({ reportedUserId: 7, reason: 'spam' });

		const [, body] = vi.mocked(api.post).mock.calls[0];
		expect(Object.keys(body as object)).toEqual(['reportedUserId', 'reason']);
	});
});
