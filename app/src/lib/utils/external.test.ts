import { describe, expect, it, vi } from 'vitest';
import { directionsUrl, openExternal } from './external';

describe('directionsUrl', () => {
	it('points at the coordinates, not at a name that may not resolve', () => {
		expect(directionsUrl(-34.6, -58.38)).toBe(
			'https://www.google.com/maps/dir/?api=1&destination=-34.6,-58.38'
		);
	});
});

describe('openExternal', () => {
	it('opens in a new context without handing over window.opener', () => {
		const open = vi.fn();
		vi.stubGlobal('window', { open });

		openExternal('https://example.test/');

		expect(open).toHaveBeenCalledWith('https://example.test/', '_blank', 'noopener');
		vi.unstubAllGlobals();
	});
});
