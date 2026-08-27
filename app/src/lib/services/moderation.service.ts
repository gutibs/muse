import { api } from './api.service';
import type { AnonymousUser } from '$lib/types';

/** Los motivos que acepta el backend (`Report.Reason`). Set cerrado: mandar
 * otro da 400. */
export const REPORT_REASONS = [
	'harassment',
	'spam',
	'inappropriate',
	'impersonation',
	'other'
] as const;

export type ReportReason = (typeof REPORT_REASONS)[number];

export interface BlockedEntry {
	id: number;
	user: AnonymousUser & { email?: string };
	createdAt: string;
}

export interface ReportPayload {
	reportedUserId: number;
	reason: ReportReason;
	/** Presente = se denuncia esa reseña; ausente = se denuncia a la persona. */
	pinId?: number;
	detail?: string;
}

/** Bloquear y denunciar.
 *
 * Bloquear es silencioso: al bloqueado no se le avisa, y la app nunca muestra
 * quién nos bloqueó a nosotros — el listado devuelve sólo los bloqueos propios.
 * Denunciar tampoco le dice nada al denunciado.
 */
export const moderationService = {
	block(userId: number): Promise<BlockedEntry> {
		return api.post('/auth/blocks/', { userId });
	},

	/** Direccionado por el id de la persona, no por el de la fila. */
	unblock(userId: number): Promise<void> {
		return api.delete(`/auth/blocks/${userId}/`);
	},

	blocks(): Promise<BlockedEntry[]> {
		return api.get('/auth/blocks/');
	},

	report(payload: ReportPayload): Promise<{ id: number }> {
		// Los opcionales se omiten en vez de mandarse vacíos: el serializer los
		// trata como ausentes, no como null.
		const body: Record<string, unknown> = {
			reportedUserId: payload.reportedUserId,
			reason: payload.reason
		};
		if (payload.pinId !== undefined) body.pinId = payload.pinId;
		if (payload.detail) body.detail = payload.detail;
		return api.post('/auth/reports/', body);
	}
};
