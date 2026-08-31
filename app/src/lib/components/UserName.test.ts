import { render } from '@testing-library/svelte';
import { describe, expect, it } from 'vitest';
import UserName from './UserName.svelte';

const INSIDER = { displayName: 'Ana', isDeleted: false, isVerifiedInsider: true };

describe('UserName', () => {
	it('shows the badge next to the name', () => {
		const { container } = render(UserName, { user: INSIDER });
		expect(container.textContent).toContain('Ana');
		expect(container.querySelector('svg')).not.toBeNull();
	});

	it('falls back to the anonymous label when there is no name', () => {
		// Este fallback estaba escrito a mano en ocho pantallas y en una
		// novena usaba el email, que el backend ya no manda.
		const { container } = render(UserName, {
			user: { displayName: '', isDeleted: false, isVerifiedInsider: false },
		});
		expect(container.textContent).toContain('Anonymous');
	});

	it('drops both the name and the badge for an erased account', () => {
		// Borrar la cuenta destruye la identidad, y el badge es identidad.
		const { container } = render(UserName, {
			user: { displayName: 'Ana', isDeleted: true, isVerifiedInsider: true },
		});
		expect(container.textContent).not.toContain('Ana');
		expect(container.querySelector('svg')).toBeNull();
	});

	it('can be asked to leave the badge out', () => {
		const { container } = render(UserName, { user: INSIDER, badge: false });
		expect(container.textContent).toContain('Ana');
		expect(container.querySelector('svg')).toBeNull();
	});

	it('shows no badge for someone who is not verified', () => {
		const { container } = render(UserName, {
			user: { displayName: 'Ana', isDeleted: false, isVerifiedInsider: false },
		});
		expect(container.querySelector('svg')).toBeNull();
	});
});
