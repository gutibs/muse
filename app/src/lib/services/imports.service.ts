import { api } from '$lib/services/api.service';

/**
 * Importar una lista de restaurantes desde un archivo (F2.G).
 *
 * El backend parsea al subir —así se sabe al instante si el archivo sirve— y
 * matchea después, desde el cron. Por eso hay que consultar el job hasta que
 * pase a `ready`, y recién ahí la persona elige qué confirmar.
 */

export type ImportState = 'pending' | 'processing' | 'ready' | 'confirmed' | 'failed';

/** Cómo resolvió cada fila del archivo. */
export type RowOutcome =
	| 'pending'
	| 'catalogue'
	| 'imported'
	| 'not_found'
	| 'ambiguous'
	| 'error'
	| 'unreadable';

export interface ImportRow {
	row: number;
	name: string;
	city?: string;
	outcome: RowOutcome;
	restaurantId?: number | null;
	detail?: string;
	/** Las que se aplicaron al restaurante. */
	tags?: string[];
	/** Las que el archivo pedía y no entraron: el lugar ya estaba descrito, o
	 * la etiqueta no existe en el catálogo. */
	tagsSkipped?: string[];
}

export interface ImportJob {
	id: number;
	source: string;
	state: ImportState;
	total: number;
	processed: number;
	matched: number;
	failed: number;
	report: ImportRow[];
	createdAt: string;
}

/** Las filas que se pueden pinear: encontradas, con restaurante resuelto. */
export function resolvedRows(job: ImportJob): ImportRow[] {
	return (job.report ?? []).filter(
		(r) => (r.outcome === 'catalogue' || r.outcome === 'imported') && r.restaurantId
	);
}

/** Las que no se pudieron resolver, para mostrarlas sin esconder el problema. */
export function unresolvedRows(job: ImportJob): ImportRow[] {
	return (job.report ?? []).filter(
		(r) => r.outcome !== 'catalogue' && r.outcome !== 'imported' && r.outcome !== 'pending'
	);
}

export const importsService = {
	upload(file: File): Promise<ImportJob> {
		const form = new FormData();
		form.append('file', file);
		return api.postForm<ImportJob>('/imports/', form);
	},

	get(id: number): Promise<ImportJob> {
		return api.get<ImportJob>(`/imports/${id}/`);
	},

	list(): Promise<ImportJob[]> {
		return api.get<ImportJob[]>('/imports/');
	},

	confirm(id: number, restaurantIds: number[]): Promise<{ created: number } & ImportJob> {
		return api.post(`/imports/${id}/confirm/`, { restaurantIds });
	}
};
