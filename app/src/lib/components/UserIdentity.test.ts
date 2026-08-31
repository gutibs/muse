import { render } from '@testing-library/svelte';
import { describe, expect, it } from 'vitest';
import UserIdentity from './UserIdentity.svelte';

const AVATAR = 'https://example.test/ana.jpg';

describe('UserIdentity', () => {
	it('puts the avatar, the name and the badge in one row', () => {
		const { container } = render(UserIdentity, {
			user: { displayName: 'Ana', avatar: AVATAR, isDeleted: false, isVerifiedInsider: true },
			subtitle: 'Hong Kong',
		});
		expect(container.querySelector('img')?.getAttribute('src')).toBe(AVATAR);
		expect(container.textContent).toContain('Ana');
		expect(container.textContent).toContain('Hong Kong');
		expect(container.querySelector('svg')).not.toBeNull();
	});

	it('leaves the subtitle out when it is empty', () => {
		const { container } = render(UserIdentity, {
			user: { displayName: 'Ana', avatar: null, isDeleted: false, isVerifiedInsider: false },
			subtitle: '',
		});
		expect(container.querySelector('p.text-xs')).toBeNull();
	});

	it('hides the avatar of an erased account', () => {
		// Su foto se borra del servidor, pero mientras el payload viejo siga
		// en pantalla no hay que pintarla.
		const { container } = render(UserIdentity, {
			user: { displayName: 'Ana', avatar: AVATAR, isDeleted: true, isVerifiedInsider: true },
		});
		expect(container.querySelector('img')).toBeNull();
		expect(container.textContent).not.toContain('Ana');
	});
});
