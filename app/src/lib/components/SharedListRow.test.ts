import { cleanup, fireEvent, render } from '@testing-library/svelte';
import { afterEach, describe, expect, it, vi } from 'vitest';
import SharedListRow from './SharedListRow.svelte';

const CURADA = {
	id: 7,
	title: 'Girls lunch',
	url: 'https://lovemuse.app/shared/abc',
	kind: 'curated' as const,
	votingEnabled: false,
};

const AUTO = { ...CURADA, id: 8, kind: 'auto' as const };

describe('SharedListRow', () => {
	afterEach(cleanup);

	it('ofrece prender la votación en una lista curada', async () => {
		const onToggleVoting = vi.fn(() => Promise.resolve());
		const { getByLabelText } = render(SharedListRow, {
			props: { list: CURADA, onCopy: vi.fn(), onRemove: vi.fn(), onToggleVoting },
		});

		await fireEvent.click(getByLabelText('Let people vote on this list'));

		expect(onToggleVoting).toHaveBeenCalledWith(7, true);
	});

	it('no la ofrece en una lista auto', () => {
		// Una lista `auto` no tiene items elegidos a mano: no hay sobre qué
		// votar, y el backend la rechaza igual.
		const { queryByLabelText } = render(SharedListRow, {
			props: { list: AUTO, onCopy: vi.fn(), onRemove: vi.fn(), onToggleVoting: vi.fn() },
		});

		expect(queryByLabelText('Let people vote on this list')).toBeNull();
	});

	it('vuelve atrás si el servidor rechaza', async () => {
		const falla = vi.fn(() => Promise.reject(new Error('offline')));
		const { getByLabelText } = render(SharedListRow, {
			props: { list: CURADA, onCopy: vi.fn(), onRemove: vi.fn(), onToggleVoting: falla },
		});

		const toggle = getByLabelText('Let people vote on this list') as HTMLInputElement;
		await fireEvent.click(toggle);
		await Promise.resolve();
		await Promise.resolve();

		expect(toggle.checked).toBe(false);
	});
});
