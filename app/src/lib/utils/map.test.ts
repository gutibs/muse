import { describe, expect, it } from 'vitest';
import { PIN_COLORS, TILE_URL } from './map';

// CARTO no falla cuando la URL está mal: sirve el mismo PNG con "API KEY
// REQUIRED" estampado encima. O sea que romper esto no da error 4xx, ni consola
// roja, ni test en rojo — se ve roto y ya. Estuvo así en producción sin que
// nadie lo reportara. Los dos detalles de abajo se encontraron comparando
// tiles byte por byte contra la CDN.

describe('TILE_URL', () => {
	it('usa la ruta rastertiles/, que es la que respeta la key', () => {
		// Sin el prefijo, `light_all/` suelta ignora la key y devuelve el tile
		// marcado — mismo md5 que pedirlo sin credencial.
		expect(TILE_URL).toContain('/rastertiles/light_all/');
	});

	it('pasa la key como `key`, no como `api_key`', () => {
		// Con `api_key` el tile vuelve marcado, idéntico a no mandar nada.
		if (!import.meta.env.VITE_CARTO_KEY) return;
		expect(TILE_URL).toMatch(/[?&]key=/);
		expect(TILE_URL).not.toMatch(/[?&]api_key=/);
	});

	it('mantiene los placeholders que reemplaza Leaflet', () => {
		// {r} es el sufijo retina (@2x). Perderlo no rompe nada visible en
		// desktop y deja el mapa borroso en el teléfono, que es donde se usa.
		for (const token of ['{s}', '{z}', '{x}', '{y}', '{r}']) {
			expect(TILE_URL, `falta ${token}`).toContain(token);
		}
	});

	it('sirve por https', () => {
		expect(TILE_URL.startsWith('https://')).toBe(true);
	});
});

describe('PIN_COLORS', () => {
	it('mantiene los tres colores distinguibles en amoled', () => {
		// La paleta taupe original era indistinguible en pantallas amoled
		// (feedback de Jess, abril 2026). Si alguien los vuelve a acercar,
		// que sea a propósito.
		const values = Object.values(PIN_COLORS);
		expect(new Set(values).size).toBe(values.length);
	});
});
