import { describe, expect, it } from 'vitest';
import { CHANNEL_DIGEST, CHANNEL_SOCIAL, routeFor } from './push.service';

// Tocar una notificación y quedarse donde estabas se siente como que la app
// está rota. Por eso `routeFor` nunca devuelve vacío: ante algo que no conoce,
// manda al feed en vez de no hacer nada.

describe('a dónde lleva tocar una notificación', () => {
	it('una solicitud lleva al perfil de quien la mandó', () => {
		expect(routeFor({ kind: 'friendship_request', actorId: 7 })).toBe('/user/7');
	});

	it('una aceptación también, porque es a esa persona a quien querés ver', () => {
		expect(routeFor({ kind: 'friendship_accepted', actorId: 9 })).toBe('/user/9');
	});

	it('acepta el id en snake_case, que es como viaja en el payload de FCM', () => {
		// FCM manda `data` como strings planos y el backend arma esas claves sin
		// pasar por el parser camelCase de DRF.
		expect(routeFor({ kind: 'friendship_request', actor_id: 3 })).toBe('/user/3');
	});

	it('sin id, cae en la lista de amigos en vez de en una ruta rota', () => {
		expect(routeFor({ kind: 'friendship_request' })).toBe('/friends');
	});

	it('el resumen diario lleva al feed', () => {
		expect(routeFor({ kind: 'friend_activity_digest' })).toBe('/feed');
	});

	it('un tipo desconocido no deja a la persona donde estaba', () => {
		expect(routeFor({ kind: 'algo_que_no_existe_todavia' })).toBe('/feed');
		expect(routeFor({})).toBe('/feed');
	});
});

// Los canales de Android. El id es un contrato entre la app y el backend que
// Android no valida: si no coinciden, el sistema usa su canal fallback —
// "Miscellaneous" en Ajustes, sin vibración, todo en la misma bolsa— y nadie se
// entera. Verificado en un Galaxy S23+ con la V1.4.0, que salió justamente así.

describe('los canales de notificación', () => {
	it('los ids son los mismos que manda el backend', async () => {
		// Mismo patrón que app-version.test.ts: el archivo del otro lado es la
		// fuente, y este test falla si alguien renombra un canal de un solo lado.
		const fs = await import('node:fs');
		const path = await import('node:path');
		const dispatch = fs.readFileSync(
			path.resolve(__dirname, '../../../../backend/notifications/services/dispatch.py'),
			'utf-8'
		);

		const delBackend = (nombre: string) => {
			const m = dispatch.match(new RegExp(`^${nombre}\\s*=\\s*"([^"]+)"`, 'm'));
			if (!m) throw new Error(`${nombre} no está en dispatch.py`);
			return m[1];
		};

		expect(CHANNEL_SOCIAL).toBe(delBackend('CHANNEL_SOCIAL'));
		expect(CHANNEL_DIGEST).toBe(delBackend('CHANNEL_DIGEST'));
	});

	it('son dos distintos, para poder callar uno sin callar el otro', () => {
		expect(CHANNEL_SOCIAL).not.toBe(CHANNEL_DIGEST);
	});
});

describe('cuándo se crean los canales', () => {
	it('los crea el arranque de la app, no el pedido de permiso', async () => {
		// El bug que este test previene: `ensureChannels` vivía dentro de
		// `enable()`, y `settings` sólo llama a `enable()` cuando el permiso
		// todavía no está dado. Quien ya había dicho que sí nunca volvía a pasar
		// por ahí, así que sus canales no se creaban nunca y todas sus
		// notificaciones salían por el fallback de FCM.
		const fs = await import('node:fs');
		const path = await import('node:path');
		const layout = fs.readFileSync(
			path.resolve(__dirname, '../../routes/+layout.svelte'),
			'utf-8'
		);
		expect(layout).toContain('ensureChannels');
	});
});
