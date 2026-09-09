import { fireEvent, render, waitFor } from '@testing-library/svelte';
import { describe, expect, it, vi } from 'vitest';
import FriendQr from './FriendQr.svelte';

const CODE = 'b1f0c0de-0000-4000-8000-000000000000';

vi.mock('$lib/services/friend-code.service', async (original) => ({
	...(await original<typeof import('$lib/services/friend-code.service')>()),
	rotateFriendCode: vi.fn(async () => 'c2e1d1ef-1111-4111-9111-111111111111')
}));

describe('FriendQr', () => {
	it('dibuja el QR del código que recibe', async () => {
		const { container } = render(FriendQr, { props: { code: CODE } });

		await waitFor(() => expect(container.querySelector('svg')).toBeTruthy());
	});

	it('rotar reemplaza el código dibujado', async () => {
		// Contra `container` y no contra el documento: no hay cleanup entre
		// tests, así que un query global encuentra el render anterior.
		const { container } = render(FriendQr, { props: { code: CODE } });
		await waitFor(() => expect(container.querySelector('svg')).toBeTruthy());
		const antes = container.querySelector('svg')!.innerHTML;

		await fireEvent.click(container.querySelector('[data-testid="rotar-codigo"]')!);

		await waitFor(() => expect(container.querySelector('svg')!.innerHTML).not.toBe(antes));
	});
});
