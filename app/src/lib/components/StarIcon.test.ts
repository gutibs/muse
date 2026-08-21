import { render } from '@testing-library/svelte';
import { describe, expect, it } from 'vitest';
import StarIcon from './StarIcon.svelte';

describe('StarIcon', () => {
	it('is hollow when the pin is not a favourite', () => {
		const { container } = render(StarIcon, { filled: false });
		expect(container.querySelector('svg')?.getAttribute('fill')).toBe('none');
	});

	it('fills in when it is', () => {
		const { container } = render(StarIcon, { filled: true });
		expect(container.querySelector('svg')?.getAttribute('fill')).toBe('currentColor');
	});

	it('is not the heart', () => {
		// El corazón ya significa el rating. Si la estrella compartiera glifo,
		// una tarjeta con las dos cosas sería ilegible.
		const { container } = render(StarIcon, {});
		expect(container.querySelector('polygon')).not.toBeNull();
		expect(container.querySelector('path')).toBeNull();
	});
});
