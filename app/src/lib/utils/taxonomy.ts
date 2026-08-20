import { i18n, t } from '$lib/i18n/index.svelte';
import type { Tag } from '$lib/types';

/**
 * Los tres ejes con los que se describe un lugar.
 *
 * `Tag.kind` en el backend tiene además `dietary`, `general` y `highlight`,
 * que existen pero no son ejes de la pantalla de pin: son atributos del
 * restaurante, no la opinión de quien lo guardó.
 */
export const AXES = ['vibe', 'occasion', 'scene'] as const;

export type Axis = (typeof AXES)[number];

export interface AxisGroup {
	kind: Axis;
	tags: Tag[];
}

/**
 * Nombre traducido de una etiqueta.
 *
 * Los nombres viven en la base en inglés y la app tiene tres idiomas, así que
 * la traducción va por slug en `translations.ts`. Una etiqueta cargada desde
 * el admin que todavía no esté traducida cae a su nombre de la base — feo,
 * pero legible, que es mejor que mostrar `tag.rooftop-secreto`.
 */
export function tagLabel(tag: Pick<Tag, 'slug' | 'name'>): string {
	const key = `tag.${tag.slug}`;
	const translated = t(key);
	return translated === key ? tag.name : translated;
}

/** Nombre del eje, en el idioma activo. */
export function axisLabel(axis: Axis): string {
	// Leer `i18n.locale` deja la llamada dentro del grafo de reactividad de
	// Svelte: sin esto, cambiar de idioma no repinta los títulos de grupo.
	void i18n.locale;
	return t(`axis.${axis}`);
}

/**
 * Reparte las etiquetas en los tres ejes, en orden fijo.
 *
 * Un eje sin etiquetas no devuelve un grupo vacío: la pantalla no tiene que
 * dibujar un título con nada debajo.
 */
export function groupByAxis(tags: Tag[]): AxisGroup[] {
	return AXES.map((kind) => ({
		kind,
		tags: tags.filter((tag) => tag.kind === kind),
	})).filter((group) => group.tags.length > 0);
}
