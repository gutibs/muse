import { describe, expect, it } from 'vitest';
import { i18n } from '$lib/i18n/index.svelte';
import { AXES, axisLabel, groupByAxis, tagLabel } from './taxonomy';
import type { Tag } from '$lib/types';

const tag = (slug: string, kind: Tag['kind'], name = slug): Tag =>
	({ id: 1, slug, kind, name }) as Tag;

describe('tagLabel', () => {
	it('translates a known tag', () => {
		i18n.setLocale('es');
		expect(tagLabel(tag('date-night', 'occasion', 'Date Night'))).toBe('Cita');
		i18n.setLocale('it');
		expect(tagLabel(tag('date-night', 'occasion', 'Date Night'))).toBe('Serata romantica');
	});

	it('falls back to the name from the database', () => {
		// El catálogo puede crecer desde el admin: una etiqueta nueva no
		// traducida tiene que mostrarse igual, no como "tag.whatever".
		i18n.setLocale('es');
		expect(tagLabel(tag('rooftop-secreto', 'scene', 'Rooftop secreto'))).toBe('Rooftop secreto');
	});
});

describe('groupByAxis', () => {
	it('keeps only the three axes, in a fixed order', () => {
		const tags = [
			tag('quiet', 'vibe'),
			tag('date-night', 'occasion'),
			tag('live-music', 'scene'),
			// dietary y general existen pero no son ejes de la pantalla de pin
			tag('vegetarian', 'dietary'),
			tag('recommended', 'highlight'),
		];

		const groups = groupByAxis(tags);

		expect(groups.map((g) => g.kind)).toEqual(['vibe', 'occasion', 'scene']);
		expect(groups.flatMap((g) => g.tags.map((t) => t.slug))).toEqual([
			'quiet',
			'date-night',
			'live-music',
		]);
	});

	it('drops an axis with no tags instead of showing an empty group', () => {
		const groups = groupByAxis([tag('quiet', 'vibe')]);
		expect(groups).toHaveLength(1);
	});
});

describe('axisLabel', () => {
	it('names each axis in the active language', () => {
		i18n.setLocale('es');
		expect(AXES.map(axisLabel)).toEqual(['Ambiente', 'Ocasión', 'Características']);
		i18n.setLocale('en');
		expect(AXES.map(axisLabel)).toEqual(['Vibe', 'Occasion', 'Features']);
	});
});
