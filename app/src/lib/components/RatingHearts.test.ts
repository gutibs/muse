import { render } from '@testing-library/svelte';
import { describe, expect, it } from 'vitest';
import RatingHearts from './RatingHearts.svelte';

/** Hearts are "empty" when they carry the muted colour class. */
function counts(container: HTMLElement) {
	const hearts = [...container.querySelectorAll('svg')];
	const empty = hearts.filter((h) => h.classList.contains('text-cream-dark'));
	return { total: hearts.length, filled: hearts.length - empty.length };
}

describe('RatingHearts', () => {
	it('always renders five hearts', () => {
		const { container } = render(RatingHearts, { value: 3 });
		expect(counts(container).total).toBe(5);
	});

	it.each([
		[0, 0],
		[1, 1],
		[3, 3],
		[5, 5],
	])('fills %i hearts for value %i', (value, expected) => {
		const { container } = render(RatingHearts, { value });
		expect(counts(container).filled).toBe(expected);
	});

	it('rounds a fractional average, as restaurant pages pass it straight through', () => {
		expect(counts(render(RatingHearts, { value: 4.3 }).container).filled).toBe(4);
		expect(counts(render(RatingHearts, { value: 4.6 }).container).filled).toBe(5);
	});

	it('treats null/undefined as zero instead of crashing', () => {
		// averageRating is nullable on a restaurant with no ratings yet.
		expect(counts(render(RatingHearts, { value: null }).container).filled).toBe(0);
		expect(counts(render(RatingHearts, {}).container).filled).toBe(0);
	});

	it('applies the requested size', () => {
		const { container } = render(RatingHearts, { value: 5, size: 'sm' });
		expect(container.querySelector('svg')?.classList.contains('h-3')).toBe(true);
	});
});
