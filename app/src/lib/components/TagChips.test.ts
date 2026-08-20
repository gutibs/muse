import { cleanup, fireEvent, render } from '@testing-library/svelte';
import { afterEach, describe, expect, it } from 'vitest';
import TagChips from './TagChips.svelte';
import { i18n } from '$lib/i18n/index.svelte';
import type { Tag } from '$lib/types';

const tag = (id: number, slug: string, kind: Tag['kind'], name = slug): Tag =>
	({ id, slug, kind, name }) as Tag;

const TAGS = [
	tag(1, 'quiet', 'vibe', 'Quiet'),
	tag(2, 'date-night', 'occasion', 'Date Night'),
	tag(3, 'live-music', 'scene', 'Live Music'),
];

describe('TagChips', () => {
	// Sin esto los renders se acumulan en el mismo documento y las consultas
	// por texto encuentran los chips de la prueba anterior.
	afterEach(cleanup);

	it('shows one group per axis, with its title', () => {
		i18n.setLocale('en');
		const { getByText } = render(TagChips, { tags: TAGS, grouped: true });

		expect(getByText('Vibe')).toBeTruthy();
		expect(getByText('Occasion')).toBeTruthy();
		expect(getByText('Features')).toBeTruthy();
	});

	it('translates the tag, not just the axis', () => {
		i18n.setLocale('es');
		const { getByText } = render(TagChips, { tags: TAGS, grouped: true });
		expect(getByText('Cita')).toBeTruthy();
	});

	it('marks a selected chip as pressed', async () => {
		i18n.setLocale('en');
		const { getByRole } = render(TagChips, { tags: TAGS, selected: [] });
		const chip = getByRole('button', { name: 'Quiet' });

		expect(chip.getAttribute('aria-pressed')).toBe('false');
		await fireEvent.click(chip);
		expect(chip.getAttribute('aria-pressed')).toBe('true');
	});

	it('shows a suggested chip as a suggestion, not as a choice', () => {
		// Si una sugerencia del sistema se ve igual que algo que el usuario
		// eligió, termina publicando una etiqueta que nunca puso.
		i18n.setLocale('en');
		const { getByRole } = render(TagChips, {
			tags: TAGS,
			selected: [3],
			suggested: ['live-music'],
		});

		const chip = getByRole('button', { name: /Live Music/ });
		expect(chip.dataset.suggested).toBe('true');
		expect(chip.textContent).toContain('suggested');
	});

	it('does not mark a suggestion the user has turned off', () => {
		const { getByRole } = render(TagChips, {
			tags: TAGS,
			selected: [],
			suggested: ['live-music'],
		});
		expect(getByRole('button', { name: 'Live Music' }).dataset.suggested).toBeUndefined();
	});

	it('renders nothing clickable in readonly mode', () => {
		const { container } = render(TagChips, { tags: TAGS, readonly: true });
		expect(container.querySelector('button')).toBeNull();
	});

	it('keeps a 44px touch target on every chip', () => {
		// Mínimo de la guía de iOS, y regla del proyecto para cualquier cosa
		// que se toque con el dedo.
		const { getAllByRole } = render(TagChips, { tags: TAGS, selected: [] });
		for (const chip of getAllByRole('button')) {
			expect(chip.className).toContain('min-h-11');
		}
	});
});
