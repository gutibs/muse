import { beforeEach, describe, expect, it, vi } from 'vitest';
import { api } from './api.service';
import { compareVersions, checkVersion } from './version.service';

vi.mock('./api.service', () => ({
	api: { getAnon: vi.fn() }
}));

describe('comparar versiones', () => {
	it('compara como número y no como texto', () => {
		// El bug que justifica escribir esto en vez de usar `<`: como string,
		// '1.10.0' < '1.9.0' es verdadero. Con esa comparación, una app al día
		// se ve como vieja y la persona queda bloqueada sin poder hacer nada.
		expect(compareVersions('1.10.0', '1.9.0')).toBeGreaterThan(0);
		expect(compareVersions('1.9.0', '1.10.0')).toBeLessThan(0);
	});

	it('dos iguales son iguales', () => {
		expect(compareVersions('1.4.1', '1.4.1')).toBe(0);
	});

	it('tolera la V que usa build.gradle', () => {
		// `build.gradle` escribe V1.4.1 y `package.json` 1.4.1. Las dos formas
		// terminan pasando por acá.
		expect(compareVersions('V1.4.1', '1.4.1')).toBe(0);
	});

	it('completa con ceros lo que falta', () => {
		expect(compareVersions('1.4', '1.4.0')).toBe(0);
		expect(compareVersions('2', '1.9.9')).toBeGreaterThan(0);
	});
});

describe('qué hacer con la versión instalada', () => {
	beforeEach(() => {
		vi.mocked(api.getAnon).mockReset();
	});

	const politica = (min: string, latest: string, storeUrl = 'https://x.test/apk') =>
		vi.mocked(api.getAnon).mockResolvedValue({ minSupported: min, latest, storeUrl });

	it('por debajo del mínimo, bloquea', async () => {
		politica('1.3.0', '1.4.1');
		const res = await checkVersion('1.2.0');
		expect(res.state).toBe('blocked');
		expect(res.storeUrl).toBe('https://x.test/apk');
	});

	it('entre el mínimo y la última, sugiere', async () => {
		politica('1.3.0', '1.4.1');
		expect((await checkVersion('1.3.5')).state).toBe('outdated');
	});

	it('justo en el mínimo no bloquea', async () => {
		politica('1.3.0', '1.4.1');
		expect((await checkVersion('1.3.0')).state).toBe('outdated');
	});

	it('al día, no molesta', async () => {
		politica('1.3.0', '1.4.1');
		expect((await checkVersion('1.4.1')).state).toBe('ok');
	});

	it('más nueva que la publicada tampoco molesta', async () => {
		// Pasa en cada build de desarrollo, y con un APK repartido a mano antes
		// de actualizar la política.
		politica('1.3.0', '1.4.1');
		expect((await checkVersion('1.5.0')).state).toBe('ok');
	});

	// Lo que sigue es el corazón del diseño: **falla abierto**. Un chequeo de
	// versión que falla cerrado convierte cualquier caída del backend en todas
	// las apps del mundo bloqueadas, que es peor que el problema que resuelve.

	it('si el backend no contesta, entra igual', async () => {
		vi.mocked(api.getAnon).mockRejectedValue(new Error('timeout'));
		expect((await checkVersion('1.0.0')).state).toBe('ok');
	});

	it('si la respuesta viene rota, entra igual', async () => {
		vi.mocked(api.getAnon).mockResolvedValue({ minSupported: 'ayer', latest: null });
		expect((await checkVersion('1.0.0')).state).toBe('ok');
	});

	it('si la respuesta viene vacía, entra igual', async () => {
		vi.mocked(api.getAnon).mockResolvedValue({});
		expect((await checkVersion('1.0.0')).state).toBe('ok');
	});

	it('sin versión instalada legible, entra igual', async () => {
		politica('1.3.0', '1.4.1');
		expect((await checkVersion('')).state).toBe('ok');
	});

	it('bloquea aunque no haya a dónde mandar a la persona', async () => {
		// `store_url` arranca vacío porque las tiendas no están aprobadas. La
		// pantalla tiene que saber mostrarse sin botón en vez de romperse.
		politica('1.3.0', '1.4.1', '');
		const res = await checkVersion('1.0.0');
		expect(res.state).toBe('blocked');
		expect(res.storeUrl).toBe('');
	});
});

describe('a qué plataforma le pide la política', () => {
	it('manda la plataforma real, no una adivinada', async () => {
		// Si esto pidiera siempre 'web', el backend contestaría la política
		// vacía y nada bloquearía nunca: el mecanismo entero inerte, en
		// silencio. `Capacitor.getPlatform()` devuelve 'web' en los tests.
		vi.mocked(api.getAnon).mockResolvedValue({ minSupported: '1.0.0', latest: '1.0.0' });
		await checkVersion('1.0.0');
		expect(vi.mocked(api.getAnon).mock.calls[0][0]).toContain('platform=');
	});
});
