import { cleanup, fireEvent, render, waitFor } from '@testing-library/svelte';
import { afterEach, describe, expect, it, vi } from 'vitest';
import VoteList from './VoteList.svelte';

const ITEMS = [
	{ itemId: 1, name: 'Ho Lee Fook', voteCount: 3, hasVoted: false },
	{ itemId: 2, name: 'Yardbird', voteCount: 1, hasVoted: true },
];

describe('VoteList', () => {
	// Sin `globals` en la config de vitest no hay auto-cleanup: los renders
	// se acumulan en el body y `getByLabelText` encuentra dos botones.
	afterEach(cleanup);

	it('marca el tick y sube el número sin esperar al servidor', async () => {
		// Esta pantalla se abre desde un chat grupal: esperar el round-trip
		// para ver el propio tick se siente roto.
		const nunca = vi.fn(() => new Promise<void>(() => {}));
		const { getByLabelText, getByTestId } = render(VoteList, {
			props: { items: ITEMS, onVote: nunca },
		});

		await fireEvent.click(getByLabelText('Vote for Ho Lee Fook'));

		expect(getByTestId('vote-count-1').textContent).toBe('4');
		expect(nunca).toHaveBeenCalledWith(1, true);
	});

	it('vuelve atrás si el servidor rechaza', async () => {
		const falla = vi.fn(() => Promise.reject(new Error('offline')));
		const { getByLabelText, getByTestId } = render(VoteList, {
			props: { items: ITEMS, onVote: falla },
		});

		await fireEvent.click(getByLabelText('Vote for Ho Lee Fook'));

		await waitFor(() => expect(getByTestId('vote-count-1').textContent).toBe('3'));
	});

	it('destildar baja el número', async () => {
		const ok = vi.fn(() => Promise.resolve());
		const { getByLabelText, getByTestId } = render(VoteList, {
			props: { items: ITEMS, onVote: ok },
		});

		await fireEvent.click(getByLabelText('Remove vote for Yardbird'));

		expect(getByTestId('vote-count-2').textContent).toBe('0');
		expect(ok).toHaveBeenCalledWith(2, false);
	});

	it('no deja votar dos veces mientras la primera está en vuelo', async () => {
		// Sin esto, dos toques rápidos mandan dos requests y el rollback de
		// una pisa el estado de la otra.
		const lento = vi.fn(() => new Promise<void>(() => {}));
		const { getByLabelText } = render(VoteList, {
			props: { items: ITEMS, onVote: lento },
		});

		const boton = getByLabelText('Vote for Ho Lee Fook');
		await fireEvent.click(boton);
		await fireEvent.click(boton);

		expect(lento).toHaveBeenCalledTimes(1);
	});

	it('adopta los conteos que llegan del servidor', async () => {
		// El estado local no puede ser la única fuente: cuando la página
		// recarga la lista, los votos de los demás tienen que aparecer.
		const { getByTestId, rerender } = render(VoteList, {
			props: { items: ITEMS, onVote: vi.fn(() => Promise.resolve()) },
		});

		await rerender({
			items: [
				{ itemId: 1, name: 'Ho Lee Fook', voteCount: 9, hasVoted: true },
				{ itemId: 2, name: 'Yardbird', voteCount: 1, hasVoted: true },
			],
			onVote: vi.fn(() => Promise.resolve()),
		});

		expect(getByTestId('vote-count-1').textContent).toBe('9');
	});

	it('no deja que una recarga pise un voto todavía en vuelo', async () => {
		const nunca = vi.fn(() => new Promise<void>(() => {}));
		const { getByLabelText, getByTestId, rerender } = render(VoteList, {
			props: { items: ITEMS, onVote: nunca },
		});

		await fireEvent.click(getByLabelText('Vote for Ho Lee Fook'));
		await rerender({ items: ITEMS, onVote: nunca });

		expect(getByTestId('vote-count-1').textContent).toBe('4');
	});
});
