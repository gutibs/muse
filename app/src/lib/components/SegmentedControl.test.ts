import { afterEach, describe, expect, it } from 'vitest';
import { cleanup, fireEvent, render } from '@testing-library/svelte';
import SegmentedControl from './SegmentedControl.svelte';

const OPTIONS = [
	{ value: 'public', label: 'Everyone' },
	{ value: 'friends', label: 'Friends' },
	{ value: 'private', label: 'Only me' },
];

describe('SegmentedControl', () => {
	afterEach(cleanup);

	it('renders one button per option', () => {
		const { getByRole } = render(SegmentedControl, { options: OPTIONS, value: 'public' });

		for (const option of OPTIONS) {
			expect(getByRole('button', { name: option.label })).toBeTruthy();
		}
	});

	it('marks only the selected option as pressed', () => {
		const { getByRole } = render(SegmentedControl, { options: OPTIONS, value: 'friends' });

		expect(getByRole('button', { name: 'Friends' }).getAttribute('aria-pressed')).toBe('true');
		expect(getByRole('button', { name: 'Everyone' }).getAttribute('aria-pressed')).toBe('false');
	});

	it('selects the option that was tapped', async () => {
		const { getByRole } = render(SegmentedControl, { options: OPTIONS, value: 'public' });

		await fireEvent.click(getByRole('button', { name: 'Only me' }));

		expect(getByRole('button', { name: 'Only me' }).getAttribute('aria-pressed')).toBe('true');
		expect(getByRole('button', { name: 'Everyone' }).getAttribute('aria-pressed')).toBe('false');
	});

	it('never leaves the selection empty: tapping the selected option keeps it', async () => {
		// A diferencia de RatingStars, que sí vuelve a 0 si repetís el toque:
		// acá no existe "sin valor", el pin siempre tiene un nivel.
		const { getByRole } = render(SegmentedControl, { options: OPTIONS, value: 'private' });

		await fireEvent.click(getByRole('button', { name: 'Only me' }));

		expect(getByRole('button', { name: 'Only me' }).getAttribute('aria-pressed')).toBe('true');
	});
});

describe('SegmentedControl onchange', () => {
	afterEach(cleanup);

	it('reports the option that was tapped', async () => {
		const seen: string[] = [];
		const { getByRole } = render(SegmentedControl, {
			options: OPTIONS,
			value: 'public',
			onchange: (v: string) => seen.push(v),
		});

		await fireEvent.click(getByRole('button', { name: 'Friends' }));

		expect(seen).toEqual(['friends']);
	});

	it('stays quiet when the tapped option was already selected', async () => {
		// Ajustes persiste en cada aviso: sin esto, volver a tocar la opción
		// activa mandaría un PATCH que no cambia nada.
		const seen: string[] = [];
		const { getByRole } = render(SegmentedControl, {
			options: OPTIONS,
			value: 'friends',
			onchange: (v: string) => seen.push(v),
		});

		await fireEvent.click(getByRole('button', { name: 'Friends' }));

		expect(seen).toEqual([]);
	});
});
