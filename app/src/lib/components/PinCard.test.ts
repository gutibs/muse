import { fireEvent, render } from '@testing-library/svelte';
import { createRawSnippet } from 'svelte';
import { describe, expect, it } from 'vitest';
import PinCard from './PinCard.svelte';

const children = createRawSnippet(() => ({
	render: () => '<p>Bar Nacional</p>',
}));

const PHOTO = 'https://example.test/photo.jpg';

describe('PinCard', () => {
	it('renders a link when given an href', () => {
		const { container } = render(PinCard, { href: '/restaurant/7', children });
		expect(container.querySelector('a')?.getAttribute('href')).toBe('/restaurant/7');
		expect(container.querySelector('button')).toBeNull();
	});

	it('renders a button when given an onclick', () => {
		const { container } = render(PinCard, { onclick: () => {}, children });
		expect(container.querySelector('button')).not.toBeNull();
		expect(container.querySelector('a')).toBeNull();
	});

	it('renders a plain container when it is neither', () => {
		const { container } = render(PinCard, { children });
		expect(container.querySelector('a')).toBeNull();
		expect(container.querySelector('button')).toBeNull();
		expect(container.textContent).toContain('Bar Nacional');
	});

	it('omits the image when the restaurant has no photo', () => {
		const { container } = render(PinCard, { children });
		expect(container.querySelector('img')).toBeNull();
	});

	it('drops the image when it fails to load', async () => {
		// A Google photo ref expires and starts answering 4xx. Without this the
		// card kept the broken-image glyph on screen.
		const { container } = render(PinCard, { imageUrl: PHOTO, imageAlt: 'Bar Nacional', children });
		const img = container.querySelector('img');
		expect(img).not.toBeNull();

		await fireEvent.error(img!);

		expect(container.querySelector('img')).toBeNull();
		expect(container.textContent).toContain('Bar Nacional');
	});
});
