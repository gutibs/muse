import { fireEvent, render } from '@testing-library/svelte';
import { createRawSnippet } from 'svelte';
import { describe, expect, it, vi } from 'vitest';
import BottomSheet from './BottomSheet.svelte';

const children = createRawSnippet(() => ({ render: () => '<p>contenido</p>' }));

function backdrop(container: HTMLElement): HTMLElement {
	const el = container.querySelector('[data-testid="sheet-backdrop"]');
	if (!el) throw new Error('no está el backdrop en pantalla');
	return el as HTMLElement;
}

describe('BottomSheet', () => {
	it('aplica las safe areas, que es lo que cada copia se olvidaba', () => {
		const { container } = render(BottomSheet, { children });
		expect(backdrop(container).style.paddingBottom).toBe('var(--sab)');
	});

	it('tocar el fondo cierra cuando el diálogo se puede descartar', async () => {
		const onclose = vi.fn();
		const { container } = render(BottomSheet, { children, onclose });

		await fireEvent.click(backdrop(container));

		expect(onclose).toHaveBeenCalledOnce();
	});

	it('tocar adentro del panel no cierra', async () => {
		const onclose = vi.fn();
		const { container } = render(BottomSheet, { children, onclose });

		const panel = container.querySelector('[data-testid="sheet-panel"]');
		await fireEvent.click(panel as Element);

		expect(onclose).not.toHaveBeenCalled();
	});

	it('sin onclose el fondo no hace nada: hay diálogos que exigen respuesta', async () => {
		const { container } = render(BottomSheet, { children });

		await fireEvent.click(backdrop(container));

		expect(container.querySelector('[data-testid="sheet-panel"]')).not.toBeNull();
	});
});
