import { t } from '$lib/i18n/index.svelte';
import type { PinVisibility } from '$lib/types';

/** De más abierto a más cerrado: el orden es la explicación. */
export const VISIBILITY_LEVELS: PinVisibility[] = ['public', 'friends', 'private'];

/**
 * El nivel que un pin muestra hoy: el suyo, o el del perfil si nunca eligió.
 *
 * `Pin.visibility` en null no significa "público" sino "lo que diga mi
 * perfil", así que la pantalla tiene que resolverlo antes de pintar el
 * selector — si no, un pin heredado se vería siempre como público.
 */
export function effectiveVisibility(
	pinLevel: PinVisibility | null | undefined,
	profileDefault: PinVisibility
): PinVisibility {
	return pinLevel ?? profileDefault;
}

/**
 * Qué mandar al backend, que puede ser nada.
 *
 * Si la persona deja el selector donde estaba, no se manda: un pin que
 * heredaba sigue heredando y se mueve solo cuando cambie la preferencia del
 * perfil. Mandar siempre el valor elegido congelaría cada pin nuevo con
 * nivel propio y esa preferencia dejaría de servir para nada.
 */
export function visibilityToSubmit(
	picked: PinVisibility,
	pinLevel: PinVisibility | null | undefined,
	profileDefault: PinVisibility
): PinVisibility | undefined {
	return picked === effectiveVisibility(pinLevel, profileDefault) ? undefined : picked;
}

/**
 * Las tres opciones con su etiqueta traducida, para el selector.
 *
 * Es una función y no una constante porque el idioma se cambia en caliente
 * desde Ajustes: una constante congelaría las etiquetas del idioma que
 * estaba activo cuando se importó el módulo.
 */
export function VISIBILITY_OPTIONS(): { value: PinVisibility; label: string }[] {
	return VISIBILITY_LEVELS.map((value) => ({ value, label: t(`pin.visibility.${value}`) }));
}
