import { describe, expect, it } from 'vitest';
import { suggestOccasion } from './suggest-occasion';

// Los tests fijan la fecha a mano: una sugerencia que depende del reloj de
// quien corre la suite es una suite que falla los domingos.
const at = (iso: string) => new Date(iso);

describe('suggestOccasion', () => {
	it('suggests brunch on a weekend morning', () => {
		expect(suggestOccasion(at('2026-08-23T11:00:00'))).toBe('brunch');
	});

	it('suggests a business lunch on a weekday midday', () => {
		expect(suggestOccasion(at('2026-08-19T13:00:00'))).toBe('business-lunch');
	});

	it('suggests drinks late at night', () => {
		expect(suggestOccasion(at('2026-08-21T23:30:00'))).toBe('drinks-bar');
	});

	it('suggests a date night on a friday evening', () => {
		expect(suggestOccasion(at('2026-08-21T20:30:00'))).toBe('date-night');
	});

	it('suggests nothing when the hour says nothing', () => {
		// Un martes a las cinco de la tarde no es ninguna ocasión en
		// particular, y adivinar sería peor que callarse.
		expect(suggestOccasion(at('2026-08-18T17:00:00'))).toBeNull();
	});

	it('does not treat a weekday midday as brunch', () => {
		expect(suggestOccasion(at('2026-08-19T11:00:00'))).toBeNull();
	});
});
