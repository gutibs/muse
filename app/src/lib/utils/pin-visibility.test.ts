import { describe, expect, it } from 'vitest';
import { i18n } from '$lib/i18n/index.svelte';
import { VISIBILITY_OPTIONS, effectiveVisibility, visibilityToSubmit } from './pin-visibility';

describe('effectiveVisibility', () => {
	it('uses the pin own level when it has one', () => {
		expect(effectiveVisibility('private', 'public')).toBe('private');
	});

	it('falls back to the profile default when the pin has none', () => {
		expect(effectiveVisibility(null, 'friends')).toBe('friends');
	});
});

describe('visibilityToSubmit', () => {
	it('sends nothing when the pick matches what the pin already shows', () => {
		// El pin sigue heredando: si mandáramos el valor igual, el pin
		// quedaría con nivel propio y dejaría de moverse cuando cambie la
		// preferencia del perfil, que es justo lo que el nivel NULL evita.
		expect(visibilityToSubmit('public', null, 'public')).toBeUndefined();
	});

	it('sends the level when the pick differs from the inherited default', () => {
		expect(visibilityToSubmit('private', null, 'public')).toBe('private');
	});

	it('sends the level when the pick differs from the pin own level', () => {
		expect(visibilityToSubmit('friends', 'private', 'public')).toBe('friends');
	});

	it('sends nothing when the pick matches the level the pin already had', () => {
		expect(visibilityToSubmit('private', 'private', 'public')).toBeUndefined();
	});
});

describe('VISIBILITY_OPTIONS', () => {
	it('offers the three levels in order, from open to closed', () => {
		i18n.setLocale('en');

		expect(VISIBILITY_OPTIONS().map((o) => o.value)).toEqual(['public', 'friends', 'private']);
	});

	it('translates the labels', () => {
		i18n.setLocale('es');

		expect(VISIBILITY_OPTIONS().map((o) => o.label)).toEqual(['Todos', 'Amigos', 'Sólo yo']);
	});
});
