import { describe, expect, it, vi } from 'vitest';
import { api } from './api.service';
import { parseFriendCode, redeemFriendCode, rotateFriendCode } from './friend-code.service';

const CODE = 'b1f0c0de-0000-4000-8000-000000000000';

describe('friend-code.service', () => {
	it('canjea el código contra el endpoint del backend', async () => {
		const post = vi.spyOn(api, 'post').mockResolvedValue({ user: { id: 7 }, status: 'pending' });

		await redeemFriendCode(CODE);

		expect(post).toHaveBeenCalledWith('/auth/friend-code/', { code: CODE });
	});

	it('rota el código propio', async () => {
		const post = vi.spyOn(api, 'post').mockResolvedValue({ friendCode: CODE });

		const nuevo = await rotateFriendCode();

		expect(post).toHaveBeenCalledWith('/auth/friend-code/rotate/', {});
		expect(nuevo).toBe(CODE);
	});
});

describe('parseFriendCode', () => {
	it('saca el código del payload que lleva el QR', () => {
		expect(parseFriendCode(`muse://friend/${CODE}`)).toBe(CODE);
	});

	it('devuelve null ante un QR que no es de Muse', () => {
		expect(parseFriendCode('https://example.com/algo')).toBeNull();
		expect(parseFriendCode('')).toBeNull();
	});

	it('rechaza un payload de Muse con un código que no es un uuid', () => {
		expect(parseFriendCode('muse://friend/no-soy-un-uuid')).toBeNull();
	});
});
