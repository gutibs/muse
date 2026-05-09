import { describe, expect, it } from 'vitest';
import { buildRestaurantPopup } from './map-popup';

const baseR = {
	id: 1,
	name: 'Test',
	city: 'Buenos Aires',
	averageRating: null,
	cuisinesDetail: [],
};

describe('buildRestaurantPopup', () => {
	it('renders name and city', () => {
		const html = buildRestaurantPopup({ restaurant: baseR });
		expect(html).toContain('Test');
		expect(html).toContain('Buenos Aires');
	});

	it('escapes HTML in name to prevent XSS', () => {
		const html = buildRestaurantPopup({
			restaurant: { ...baseR, name: '<script>alert(1)</script>' },
		});
		expect(html).not.toContain('<script>');
		expect(html).toContain('&lt;script&gt;');
	});

	it('escapes HTML in city, owner, and cuisines', () => {
		const html = buildRestaurantPopup({
			restaurant: {
				...baseR,
				city: '"><img>',
				cuisinesDetail: [{ id: 1, name: 'A & B', slug: 'a-b' }],
			},
			owner: { displayName: '<b>X</b>', email: null },
			showCuisines: true,
		});
		expect(html).not.toContain('<img>');
		expect(html).not.toContain('<b>X</b>');
		expect(html).toContain('A &amp; B');
		expect(html).toContain('&lt;b&gt;X&lt;/b&gt;');
	});

	it('renders pin rating when pin is provided', () => {
		const html = buildRestaurantPopup({
			restaurant: baseR,
			pin: { rating: 4, status: 'visited' },
		});
		expect(html).toContain('♥ 4/5');
	});

	it('falls back to averageRating when no pin is provided', () => {
		const html = buildRestaurantPopup({
			restaurant: { ...baseR, averageRating: 4.25 },
		});
		expect(html).toContain('♥ 4.3'); // toFixed(1)
	});

	it('suppresses both ratings when pin is explicitly null', () => {
		const html = buildRestaurantPopup({
			restaurant: { ...baseR, averageRating: 4.25 },
			pin: null,
		});
		expect(html).not.toContain('♥');
	});

	it('shows owner byline when owner is provided', () => {
		const html = buildRestaurantPopup({
			restaurant: baseR,
			owner: { displayName: 'Juan', email: 'juan@example.com' },
		});
		expect(html).toContain('Juan');
		// Owner byline must appear before the name (top of popup).
		const ownerIdx = html.indexOf('Juan');
		const nameIdx = html.indexOf('Test');
		expect(ownerIdx).toBeLessThan(nameIdx);
	});

	it('falls back to email when displayName is empty for owner', () => {
		const html = buildRestaurantPopup({
			restaurant: baseR,
			owner: { displayName: '', email: 'juan@example.com' },
		});
		expect(html).toContain('juan@example.com');
	});

	it('wraps name in <a href> when link=true', () => {
		const html = buildRestaurantPopup({ restaurant: baseR, link: true });
		expect(html).toContain('href="/restaurant/1"');
		expect(html).toContain('>Test</a>');
	});

	it('uses <strong> when link is omitted', () => {
		const html = buildRestaurantPopup({ restaurant: baseR });
		expect(html).not.toContain('<a href');
		expect(html).toContain('<strong');
		expect(html).toContain('>Test</strong>');
	});

	it('renders status label at the bottom', () => {
		const html = buildRestaurantPopup({
			restaurant: baseR,
			pin: { rating: 5, status: 'visited' },
			statusLabel: 'Rated',
		});
		expect(html).toContain('Rated');
		// Status appears after rating
		expect(html.indexOf('♥')).toBeLessThan(html.indexOf('Rated'));
	});

	it('appends pre-built dietary HTML verbatim', () => {
		const dietary = '<br><div>BADGE</div>';
		const html = buildRestaurantPopup({
			restaurant: baseR,
			dietaryHtml: dietary,
		});
		expect(html).toContain('<div>BADGE</div>');
	});

	it('renders cuisines comma-separated when showCuisines=true', () => {
		const html = buildRestaurantPopup({
			restaurant: {
				...baseR,
				cuisinesDetail: [
					{ id: 1, name: 'Italian', slug: 'italian' },
					{ id: 2, name: 'Japanese', slug: 'japanese' },
				],
			},
			showCuisines: true,
		});
		expect(html).toContain('Italian, Japanese');
	});

	it('omits city block when city is empty', () => {
		const html = buildRestaurantPopup({ restaurant: { ...baseR, city: '' } });
		expect(html).not.toContain('font-size:12px');
	});

	it('produces deterministic shell wrapper', () => {
		const html = buildRestaurantPopup({ restaurant: baseR });
		expect(html.startsWith('<div style="font-family:Inter,sans-serif;min-width:140px;">')).toBe(
			true
		);
		expect(html.endsWith('</div>')).toBe(true);
	});
});
