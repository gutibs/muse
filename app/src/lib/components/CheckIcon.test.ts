import { render } from '@testing-library/svelte';
import { describe, expect, it } from 'vitest';
import CheckIcon from './CheckIcon.svelte';

describe('CheckIcon', () => {
	it('se dibuja con el trazo del sistema, no relleno', () => {
		// El resto de los íconos del producto son de línea. Un check sólido
		// al lado de un corazón y una estrella de trazo se ve pegado de otro
		// lado.
		const { container } = render(CheckIcon, {});
		const svg = container.querySelector('svg');
		expect(svg?.getAttribute('fill')).toBe('none');
		expect(svg?.getAttribute('stroke')).toBe('currentColor');
	});

	it('no es la estrella ni el corazón', () => {
		const { container } = render(CheckIcon, {});
		expect(container.querySelector('polyline')).not.toBeNull();
		expect(container.querySelector('polygon')).toBeNull();
	});
});
