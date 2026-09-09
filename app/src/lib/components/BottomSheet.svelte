<script lang="ts">
	/**
	 * El envoltorio de todo lo que se dibuja encima de la app: los diálogos que
	 * exigen una decisión, los que se pueden descartar y las hojas de acciones.
	 *
	 * Existe porque el markup estaba copiado en cuatro lugares y **divergió sin
	 * que nadie lo notara**: `ReportModal` y la hoja de acciones del perfil
	 * ajeno se habían quedado sin las safe areas —los botones caían dentro de
	 * la franja del indicador de inicio— y la segunda además usaba `z-40`
	 * mientras el resto usaba `z-50`, así que se dibujaba por debajo de
	 * cualquier otra capa. Es la misma historia que los tres bootstraps de
	 * Leaflet.
	 *
	 * Las safe areas van acá y no en quien lo usa: esto se dibuja por encima de
	 * `AppShell`, así que no hereda las suyas. Es la única excepción a "sólo
	 * AppShell aplica safe areas" que el CLAUDE.md admite, y por eso vive en un
	 * solo lugar.
	 *
	 * `onclose` es lo que decide si se puede descartar. Sin él, tocar afuera no
	 * hace nada: un gate de consentimiento o el pedido del resumen necesitan una
	 * respuesta, y cerrarse con un toque al costado sería tomar la decisión por
	 * la persona.
	 */
	import type { Snippet } from 'svelte';

	interface Props {
		children: Snippet;
		/** Si está, tocar el fondo cierra. Si no, el diálogo exige una respuesta. */
		onclose?: () => void;
		/** `sheet` sube desde abajo en móvil; `center` queda centrado siempre. */
		align?: 'sheet' | 'center';
	}

	let { children, onclose, align = 'sheet' }: Props = $props();
</script>

<!-- svelte-ignore a11y_click_events_have_key_events -->
<!-- svelte-ignore a11y_no_static_element_interactions -->
<div
	data-testid="sheet-backdrop"
	class="fixed inset-0 z-50 flex justify-center bg-black/40 {align === 'center'
		? 'items-center px-6'
		: 'items-end sm:items-center'}"
	style="padding-bottom: var(--sab); padding-left: var(--sal); padding-right: var(--sar);"
	onclick={onclose}
>
	<!-- svelte-ignore a11y_click_events_have_key_events -->
	<!-- svelte-ignore a11y_no_static_element_interactions -->
	<div
		data-testid="sheet-panel"
		class="w-full max-w-sm bg-white p-6 shadow-elevated {align === 'center'
			? 'rounded-card'
			: 'rounded-t-card sm:rounded-card'}"
		onclick={(e) => e.stopPropagation()}
	>
		{@render children()}
	</div>
</div>
