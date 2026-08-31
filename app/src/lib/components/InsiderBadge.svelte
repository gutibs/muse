<script lang="ts">
	/**
	 * El Verified Insider: la marca que Muse otorga a mano a quien conoce la
	 * escena local. El glifo vive sólo acá.
	 *
	 * Dos variantes porque el badge aparece en superficies de densidad muy
	 * distinta. En un feed o en una fila de amigos sólo entra el círculo —una
	 * etiqueta de texto al lado de cada nombre tapa la mitad de la pantalla—;
	 * donde hay aire (un perfil, la cabecera de una lista compartida) va con
	 * el nombre completo, que es lo que lo hace entendible sin tener que ir a
	 * buscar qué significa.
	 *
	 * Círculo lleno y no una píldora de texto como el chip de amistad: los dos
	 * conviven en la misma línea de la ficha de restaurante y tienen que
	 * distinguirse de un vistazo, por forma antes que por color.
	 */
	import { t } from '$lib/i18n/index.svelte';

	let {
		variant = 'icon',
		size = 'md',
		tone = 'brand',
		labelled = true,
		class: klass = '',
	}: {
		variant?: 'icon' | 'full';
		size?: 'sm' | 'md';
		/** `false` cuando el badge va adentro de algo que ya se nombra solo —el
		 * chip "Sólo Insiders", por ejemplo—. Si no, un lector de pantalla
		 * anuncia "Insider verificado Insiders": el glifo ahí es decoración y
		 * la etiqueta la pone el control que lo contiene. */
		labelled?: boolean;
		/** `inherit` para cuando el badge va sobre un fondo de color y tiene
		 * que tomar el color del texto que lo rodea, como en el chip activo
		 * del mapa. Prop y no una clase de más: dos `text-*` en el mismo
		 * elemento los resuelve el orden del CSS, no el del atributo. */
		tone?: 'brand' | 'inherit';
		class?: string;
	} = $props();

	const SIZES = { sm: 'h-3.5 w-3.5', md: 'h-4 w-4' };
</script>

{#snippet glyph()}
	<!-- La I queda hueca por `evenodd`: el segundo subpath se recorta del
	     círculo, así el badge toma el color del fondo que tenga detrás. -->
	<svg
		class="{SIZES[size]} shrink-0 {variant === 'icon' ? klass : ''}"
		viewBox="0 0 24 24"
		fill="currentColor"
		fill-rule="evenodd"
		clip-rule="evenodd"
		aria-hidden="true"
	>
		<path
			d="M12 2C6.477 2 2 6.477 2 12s4.477 10 10 10 10-4.477 10-10S17.523 2 12 2Zm-3 5.2h6v2.1h-1.95v5.4H15v2.1H9v-2.1h1.95V9.3H9V7.2Z"
		/>
	</svg>
{/snippet}

{#if variant === 'full'}
	<span
		class="inline-flex items-center gap-1 rounded-full bg-jade-dark/10 px-2 py-0.5 text-[11px] font-medium text-jade-dark {klass}"
	>
		{@render glyph()}
		{t('badges.insider')}
	</span>
{:else}
	<!-- El title es para quien mira con el mouse; el label accesible va
	     siempre, que es lo que lee un lector de pantalla. -->
	<span
		class="inline-flex {tone === 'brand' ? 'text-jade-dark' : ''}"
		title={labelled ? t('badges.insider') : undefined}
	>
		{@render glyph()}
		{#if labelled}
			<span class="sr-only">{t('badges.insider')}</span>
		{/if}
	</span>
{/if}
