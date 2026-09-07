import { Capacitor } from '@capacitor/core';
import { api } from '$lib/services/api.service';
import { logSilent } from '$lib/utils/logger';

/**
 * Push notifications (F2.E).
 *
 * Todo acá adentro es no-op fuera de un dispositivo: en el navegador no hay
 * plugin ni token que registrar, y la app se sirve por web sólo en
 * `/shared/<token>`. Que las funciones existan igual evita un `if` en cada
 * llamador.
 *
 * El permiso NO se pide al arrancar. Android 13+ exige `POST_NOTIFICATIONS` y
 * **un rechazo no se vuelve a preguntar**: pedirlo en la primera pantalla, sin
 * que la persona sepa todavía qué gana, es la forma más rápida de perder el
 * canal para siempre. Se pide en contexto — al mandar o aceptar una solicitud
 * de amistad, que es cuando la notificación tiene sentido.
 */

let registered = false;

/**
 * El token vive en localStorage y no sólo en memoria.
 *
 * En memoria se perdía en el caso más común: abrir la app con la sesión ya
 * guardada no pasa por `login()`, así que nada llamaba a `enable()` y
 * `currentToken` quedaba null. Al cerrar sesión no se mandaba el DELETE y la
 * fila seguía atada a la cuenta anterior — ese teléfono seguía recibiendo sus
 * notificaciones hasta 90 días. Es justo lo que la política publicada dice que
 * no pasa ("se borra cuando cerrás sesión").
 */
const TOKEN_KEY = 'muse_push_token';

function readToken(): string | null {
	try {
		return localStorage.getItem(TOKEN_KEY);
	} catch {
		return null;
	}
}

function writeToken(value: string | null) {
	try {
		if (value) localStorage.setItem(TOKEN_KEY, value);
		else localStorage.removeItem(TOKEN_KEY);
	} catch {
		// Storage bloqueado: se sigue sin recordar el token. El backend lo
		// limpia igual cuando FCM lo rechace o pasen los 90 días.
	}
}

function available(): boolean {
	return Capacitor.isNativePlatform();
}

/** Lo que el sistema dice hoy, sin abrir ningún diálogo. */
export async function permissionState(): Promise<'granted' | 'denied' | 'prompt' | 'unsupported'> {
	if (!available()) return 'unsupported';
	try {
		const { PushNotifications } = await import('@capacitor/push-notifications');
		const status = await PushNotifications.checkPermissions();
		if (status.receive === 'granted') return 'granted';
		if (status.receive === 'denied') return 'denied';
		return 'prompt';
	} catch (err) {
		logSilent('push.checkPermissions', err);
		return 'unsupported';
	}
}

/**
 * Pide el permiso si todavía no se decidió, y registra el dispositivo.
 *
 * Devuelve si quedó registrado. Llamar dos veces no hace nada la segunda: el
 * plugin ya está escuchando y el token no cambió.
 */
export async function enable(): Promise<boolean> {
	if (!available()) return false;

	try {
		const { PushNotifications } = await import('@capacitor/push-notifications');

		let status = await PushNotifications.checkPermissions();
		if (status.receive === 'prompt' || status.receive === 'prompt-with-rationale') {
			status = await PushNotifications.requestPermissions();
		}
		if (status.receive !== 'granted') return false;

		if (!registered) {
			// Los listeners van antes del register: el token llega por evento y
			// si el listener no está puesto todavía, se pierde.
			await PushNotifications.addListener('registration', (token) => {
				writeToken(token.value);
				void sendToken(token.value);
			});
			await PushNotifications.addListener('registrationError', (err) => {
				logSilent('push.registrationError', err);
			});
			registered = true;
		}

		await PushNotifications.register();
		return true;
	} catch (err) {
		logSilent('push.enable', err);
		return false;
	}
}

async function sendToken(token: string): Promise<void> {
	try {
		await api.post('/notifications/devices/', { token, platform: Capacitor.getPlatform() });
	} catch (err) {
		// Que no se registre el token no puede romper nada de lo que la persona
		// estaba haciendo: se reintenta en el próximo inicio de sesión.
		logSilent('push.sendToken', err);
	}
}

/**
 * Baja el token de este dispositivo. Se llama al cerrar sesión.
 *
 * Sin esto, el teléfono seguiría recibiendo las notificaciones de la cuenta
 * anterior — que es peor que no recibir ninguna.
 */
export async function disable(): Promise<void> {
	const token = readToken();
	if (!available() || !token) return;
	try {
		await api.delete('/notifications/devices/', { token });
	} catch (err) {
		logSilent('push.disable', err);
	} finally {
		writeToken(null);
	}
}

/**
 * A dónde lleva tocar una notificación.
 *
 * El backend manda `kind` y los ids en `data`. Si llega algo que no
 * conocemos, se abre el feed en vez de no hacer nada: quedarse en la pantalla
 * anterior después de tocar una notificación se siente como que la app está
 * rota.
 */
export function routeFor(data: Record<string, unknown>): string {
	const kind = String(data?.kind ?? '');
	const actorId = data?.actorId ?? data?.actor_id;

	if (kind === 'friendship_request' || kind === 'friendship_accepted') {
		return actorId ? `/user/${actorId}` : '/friends';
	}
	if (kind === 'friend_activity_digest') {
		return '/feed';
	}
	return '/feed';
}

/** Engancha el tap sobre una notificación con la navegación de la app. */
export async function listenForTaps(navigate: (path: string) => void): Promise<void> {
	if (!available()) return;
	try {
		const { PushNotifications } = await import('@capacitor/push-notifications');
		await PushNotifications.addListener('pushNotificationActionPerformed', (action) => {
			const data = (action.notification?.data ?? {}) as Record<string, unknown>;
			navigate(routeFor(data));
		});
	} catch (err) {
		logSilent('push.listenForTaps', err);
	}
}
