/**
 * Red de caracterización, escrita ANTES de migrar el componente a
 * `SegmentedControl`: fija lo que hace hoy para que el refactor no cambie el
 * comportamiento sin que nadie se entere.
 */
import { afterEach, describe, expect, it } from 'vitest';
import { cleanup, fireEvent, render } from '@testing-library/svelte';
import { i18n } from '$lib/i18n/index.svelte';
import StatusToggle from './StatusToggle.svelte';

describe('StatusToggle', () => {
	afterEach(cleanup);

	it('offers the two pin statuses, to_visit first', () => {
		i18n.setLocale('en');
		const { getAllByRole } = render(StatusToggle, { value: 'to_visit' });

		expect(getAllByRole('button').map((b) => b.textContent?.trim())).toEqual([
			'On the List',
			'Rated',
		]);
	});

	it('highlights the selected status', () => {
		i18n.setLocale('en');
		const { getByRole } = render(StatusToggle, { value: 'visited' });

		expect(getByRole('button', { name: 'Rated' }).className).toContain('bg-jade');
		expect(getByRole('button', { name: 'On the List' }).className).not.toContain('bg-jade');
	});

	it('moves the highlight to the status that was tapped', async () => {
		i18n.setLocale('en');
		const { getByRole } = render(StatusToggle, { value: 'to_visit' });

		await fireEvent.click(getByRole('button', { name: 'Rated' }));

		expect(getByRole('button', { name: 'Rated' }).className).toContain('bg-jade');
	});
});
