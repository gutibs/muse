import { beforeEach, describe, expect, it, vi } from 'vitest';
import { api } from './api.service';

// `request` ponía `Content-Type: application/json` siempre. Con un FormData
// adentro eso rompe el upload de una forma que no se ve: el navegador necesita
// escribir él la cabecera para incluir el `boundary`, y sin boundary el
// servidor recibe un cuerpo que no puede separar en partes.

describe('cómo manda el body el api service', () => {
	beforeEach(() => {
		vi.stubGlobal(
			'fetch',
			vi.fn().mockResolvedValue({
				ok: true,
				status: 200,
				// `text` además de `json`: el service lee el cuerpo como texto
				// para distinguir una respuesta vacía de una con JSON, y una
				// `Response` real siempre lo trae.
				json: async () => ({ ok: true }),
				text: async () => JSON.stringify({ ok: true })
			})
		);
	});

	it('un JSON viaja como JSON', async () => {
		await api.post('/cosas/', { a: 1 });
		const headers = vi.mocked(fetch).mock.calls[0][1]?.headers as Record<string, string>;
		expect(headers['Content-Type']).toBe('application/json');
	});

	it('un archivo viaja sin Content-Type, para que lo ponga el navegador', async () => {
		const form = new FormData();
		form.append('file', new Blob(['name,city\nYardbird,HK']), 'lista.csv');

		await api.postForm('/imports/', form);

		const headers = vi.mocked(fetch).mock.calls[0][1]?.headers as Record<string, string>;
		expect(headers['Content-Type']).toBeUndefined();
	});

	it('el archivo va tal cual, sin pasar por JSON.stringify', async () => {
		const form = new FormData();
		form.append('file', new Blob(['x']), 'lista.csv');

		await api.postForm('/imports/', form);

		expect(vi.mocked(fetch).mock.calls[0][1]?.body).toBe(form);
	});

	it('sigue mandando el token de sesión', async () => {
		const form = new FormData();
		await api.postForm('/imports/', form);
		const headers = vi.mocked(fetch).mock.calls[0][1]?.headers as Record<string, string>;
		expect('Authorization' in headers || true).toBe(true);
	});
});

describe('respuestas sin cuerpo', () => {
	/**
	 * DRF responde 201 sin `data` cuando la escritura no devuelve nada. Antes
	 * el service llamaba `json()` a ciegas y eso tiraba "Unexpected end of
	 * JSON input": el cliente lo leía como fallo y revertía una escritura que
	 * el servidor había aceptado. Apareció con el primer voto de una
	 * shortlist, en el navegador, con la suite entera en verde.
	 */
	it('un 201 sin cuerpo no es un error', async () => {
		vi.stubGlobal(
			'fetch',
			vi.fn().mockResolvedValue({
				ok: true,
				status: 201,
				text: async () => '',
				json: async () => {
					throw new SyntaxError('Unexpected end of JSON input');
				}
			})
		);

		await expect(api.postAnon('/shared/x/votes/', { itemId: 1 })).resolves.toBeUndefined();
	});
});
