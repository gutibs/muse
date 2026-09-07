import { Capacitor } from '@capacitor/core';
import { api } from '$lib/services/api.service';
import { logSilent } from '$lib/utils/logger';

/**
 * Si la versión instalada todavía sirve (F2.H).
 *
 * Existe por un caso real: el 2026-09-06 un teléfono tenía la V1.2.0, de antes
 * de que cambiara el contrato del registro, y la app arrancaba igual y fallaba
 * en la cara del usuario sin decir por qué.
 *
 * **Todo esto falla abierto.** Cualquier problema —el backend caído, un avión,
 * una respuesta con forma inesperada, un número de versión ilegible— deja
 * entrar. Un chequeo que falla cerrado convierte una caída del backend en todas
 * las apps del mundo bloqueadas, que es peor que el problema que resuelve.
 */

export type VersionState =
	/** Al día, o más nueva que la publicada. No se muestra nada. */
	| 'ok'
	/** Entre el mínimo y la última: se sugiere actualizar y se puede descartar. */
	| 'outdated'
	/** Por debajo del mínimo: pantalla sin salida. */
	| 'blocked';

export interface VersionCheck {
	state: VersionState;
	/** A dónde mandar a la persona. Puede venir vacío: las tiendas no están aprobadas. */
	storeUrl: string;
	latest: string;
}

const SIN_NOVEDAD: VersionCheck = { state: 'ok', storeUrl: '', latest: '' };

/**
 * `-1`, `0` o `1`, comparando como versión y no como texto.
 *
 * Escrito a mano en vez de traer una dependencia: son quince líneas y el único
 * caso que importa es el que rompe la comparación ingenua — `'1.10.0' < '1.9.0'`
 * es verdadero como string. Con eso, una app al día se ve como vieja y la
 * persona queda bloqueada sin poder hacer nada.
 *
 * Tolera la `V` de `build.gradle` y las longitudes distintas: `1.4` y `1.4.0`
 * son la misma versión.
 */
export function compareVersions(a: string, b: string): number {
	const partes = (v: string) =>
		v
			.trim()
			.replace(/^[Vv]/, '')
			.split('.')
			.map((n) => Number.parseInt(n, 10));

	const izq = partes(a);
	const der = partes(b);
	const largo = Math.max(izq.length, der.length);

	for (let i = 0; i < largo; i++) {
		const x = izq[i] ?? 0;
		const y = der[i] ?? 0;
		if (Number.isNaN(x) || Number.isNaN(y)) throw new Error(`versión ilegible: ${a} / ${b}`);
		if (x !== y) return x < y ? -1 : 1;
	}
	return 0;
}

/** Consulta la política y decide qué mostrar. Nunca lanza. */
export async function checkVersion(installed: string): Promise<VersionCheck> {
	try {
		const res = await api.getAnon<{
			minSupported?: string;
			latest?: string;
			storeUrl?: string;
		}>(`/app-version/?platform=${encodeURIComponent(platform())}`);

		const min = res?.minSupported ?? '';
		const latest = res?.latest ?? '';
		if (!min || !latest || !installed) return SIN_NOVEDAD;

		const storeUrl = res?.storeUrl ?? '';

		if (compareVersions(installed, min) < 0) {
			return { state: 'blocked', storeUrl, latest };
		}
		if (compareVersions(installed, latest) < 0) {
			return { state: 'outdated', storeUrl, latest };
		}
		return { state: 'ok', storeUrl, latest };
	} catch (err) {
		// Incluye la versión ilegible: si no se puede comparar, no se bloquea.
		logSilent('version.check', err);
		return SIN_NOVEDAD;
	}
}

function platform(): string {
	// `Capacitor.getPlatform()` y no `globalThis.Capacitor`: si ese global no
	// estuviera con ese nombre exacto, esto devolvería 'web' en un teléfono, el
	// backend contestaría la política vacía —que no bloquea a nadie— y el
	// mecanismo entero quedaría inerte sin una sola línea de error.
	return Capacitor.getPlatform();
}
