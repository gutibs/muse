import type { Action } from 'svelte/action';

/** Cuánto de la tarjeta tiene que estar en pantalla para contar como vista. */
const VISIBLE_RATIO = 0.5;
/**
 * Y cuánto tiempo. Un scroll rápido cruza media pantalla de tarjetas en un
 * segundo: sin esta espera, "lo vio" incluye todo lo que pasó volando por
 * abajo del pulgar.
 */
const MIN_VISIBLE_MS = 500;

export interface VisibilityParams {
	/** Se llama una vez, cuando el nodo estuvo visible el tiempo mínimo. */
	onVisible?: () => void;
}

/**
 * Avisa cuando el nodo estuvo de verdad a la vista.
 *
 * Se desconecta después del primer aviso: el dedupe por sesión vive en
 * `analytics.service`, pero no tiene sentido seguir observando algo que ya
 * se contó.
 */
export const trackVisibility: Action<HTMLElement, VisibilityParams | undefined> = (
	node,
	params
) => {
	let observer: IntersectionObserver | null = null;
	let pending: ReturnType<typeof setTimeout> | null = null;
	// El aviso es una sola vez por nodo, y no confiamos en que `disconnect()`
	// sea suficiente: alcanza con que quede una entrada en vuelo para contar
	// la misma tarjeta dos veces.
	let reported = false;

	function stop() {
		if (pending !== null) {
			clearTimeout(pending);
			pending = null;
		}
		observer?.disconnect();
		observer = null;
	}

	function start(current: VisibilityParams | undefined) {
		stop();
		const onVisible = current?.onVisible;
		// Sin callback no hay nada que observar; y en un runtime sin
		// IntersectionObserver (tests, WebView viejo) la app funciona igual,
		// simplemente no se cuenta la vista.
		if (reported || !onVisible || typeof IntersectionObserver === 'undefined') return;

		observer = new IntersectionObserver(
			(entries) => {
				if (reported) return;
				const visible = entries.some((e) => e.isIntersecting);
				if (visible && pending === null) {
					pending = setTimeout(() => {
						pending = null;
						reported = true;
						stop();
						onVisible();
					}, MIN_VISIBLE_MS);
				} else if (!visible && pending !== null) {
					clearTimeout(pending);
					pending = null;
				}
			},
			{ threshold: VISIBLE_RATIO }
		);
		observer.observe(node);
	}

	start(params);

	return {
		update: start,
		destroy: stop,
	};
};
