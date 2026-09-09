import { api } from './api.service';
import type { AnonymousUser } from '$lib/types';

/** Lo que codifica el QR. No es una URL de lovemuse.app a propósito: esa ruta
 * no existe en nginx —sólo `/shared/` se sirve por web— así que la cámara del
 * sistema llevaría a un 404. Con un scheme propio, el QR sólo significa algo
 * dentro de la app, que es donde se canjea. */
const PREFIJO = 'muse://friend/';

const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

export type RedeemResult = {
	user: AnonymousUser;
	status: 'pending' | 'accepted' | 'declined';
};

/** El texto que va adentro del QR de esta persona. */
export function friendCodePayload(code: string): string {
	return `${PREFIJO}${code}`;
}

/** El código que trae un QR escaneado, o null si el QR no es de Muse.
 * Valida la forma acá y no en el servidor porque un QR de cualquier otra cosa
 * es lo más común que va a leer la cámara, y no tiene sentido gastar una
 * request —ni una cuota de throttle— en cada cartel de la calle. */
export function parseFriendCode(texto: string): string | null {
	if (!texto.startsWith(PREFIJO)) return null;
	const code = texto.slice(PREFIJO.length);
	return UUID.test(code) ? code : null;
}

export function redeemFriendCode(code: string): Promise<RedeemResult> {
	return api.post<RedeemResult>('/auth/friend-code/', { code });
}

export async function rotateFriendCode(): Promise<string> {
	const res = await api.post<{ friendCode: string }>('/auth/friend-code/rotate/', {});
	return res.friendCode;
}
