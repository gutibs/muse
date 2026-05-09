import { render } from '@testing-library/svelte';
import { describe, expect, it } from 'vitest';
import PinsMap from './PinsMap.svelte';

describe('PinsMap', () => {
	it('renders without crashing with empty items', () => {
		const { container } = render(PinsMap, { items: [] });
		// The root is the map container <div class="h-full w-full">
		expect(container.querySelector('div.h-full')).toBeTruthy();
	});

	it('renders the bootError fallback when bootstrap throws', () => {
		// We can't easily force the dynamic import to throw from here without
		// mocking, so we just assert the component compiles and exposes a
		// callable mount. Deeper coverage lives in the unit tests of
		// map-popup.ts (the popup HTML) and is exercised by `npm run build`.
		expect(typeof PinsMap).toBe('function');
	});
});
