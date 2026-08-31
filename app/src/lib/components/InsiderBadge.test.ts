import { render } from '@testing-library/svelte';
import { describe, expect, it } from 'vitest';
import InsiderBadge from './InsiderBadge.svelte';

describe('InsiderBadge', () => {
	it('says what it is even when it is only a glyph', () => {
		// En las pantallas densas el badge es un círculo sin texto. Si además
		// no dijera nada a un lector de pantalla, sería decoración.
		const { container } = render(InsiderBadge, { variant: 'icon' });
		expect(container.querySelector('.sr-only')?.textContent).toBe('Verified Insider');
	});

	it('spells out the name in the full variant', () => {
		const { container } = render(InsiderBadge, { variant: 'full' });
		expect(container.textContent).toContain('Verified Insider');
		expect(container.querySelector('.sr-only')).toBeNull();
	});

	it('takes the surrounding colour when asked to', () => {
		// Sobre el chip activo del mapa el badge va en blanco. Dos `text-*` en
		// el mismo elemento los resuelve el CSS, no el orden del atributo, así
		// que el color de marca tiene que poder apagarse.
		const { container } = render(InsiderBadge, { variant: 'icon', tone: 'inherit' });
		expect(container.innerHTML).not.toContain('text-jade-dark');
	});

	it('paints the brand colour by default', () => {
		const { container } = render(InsiderBadge, { variant: 'icon' });
		expect(container.innerHTML).toContain('text-jade-dark');
	});
});
