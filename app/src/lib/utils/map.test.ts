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

describe('createMap — el encuadre de un conjunto disperso', () => {
	it('deja alejarse lo suficiente para encuadrar dos continentes', async () => {
		// Con minZoom 3 el mundo mide 2048px: Londres y Hong Kong abarcan 114°
		// de longitud, o sea 650px, y no entran en los ~340px útiles de un
		// teléfono. `fitBounds` encuadraba igual, al zoom mínimo permitido, y
		// dejaba los extremos afuera: el mapa de una lista compartida se abría
		// vacío. Verificado en el navegador midiendo la posición de cada marker
		// contra el contenedor.
		//
		// El límite no puede bajar a 1: ahí el mundo (512px) es más chico que
		// el alto de un teléfono y `maxBounds` con viscosidad dura descentra el
		// encuadre.
		const { createMap } = await import('./map');
		const opciones: Record<string, unknown>[] = [];
		const fakeLeaflet = {
			map: (_el: unknown, opts: Record<string, unknown>) => {
				opciones.push(opts);
				return { setView: () => ({}) };
			},
		};
		// setView devuelve el mapa; el resto de createMap necesita más de
		// Leaflet, así que sólo nos interesa que la opción llegue.
		try {
			createMap(fakeLeaflet as never, document.createElement('div'));
		} catch {
			// createMap sigue y falla al agregar capas sobre el doble falso: lo
			// que se mide es la opción que ya quedó registrada arriba.
		}

		expect(opciones[0]?.minZoom).toBe(2);
	});
});
