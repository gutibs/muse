<script lang="ts">
	import type { Snippet } from 'svelte';

	// `banner` es un slot opcional que se dibuja **arriba** del contenido y lo
	// empuja hacia abajo, en vez de superponerse. Lo usa el aviso de versión
	// nueva: flotando tapaba el encabezado de cada pantalla, y pegado abajo
	// tapaba la barra de navegación entera.
	let { children, banner }: { children: Snippet; banner?: Snippet } = $props();
</script>

<div
	class="flex h-full w-full flex-col"
	style="
		padding-top: var(--sat);
		padding-bottom: var(--sab);
		padding-left: var(--sal);
		padding-right: var(--sar);
	"
>
	{#if banner}{@render banner()}{/if}
	<!--
		`min-h-0` no es decorativo: sin él, un hijo con `h-full` desborda el flex
		en vez de encogerse, y el scroll interno de las pantallas deja de
		funcionar. Con el banner ausente el comportamiento es idéntico al de
		antes, porque este div ocupa todo el alto disponible.
	-->
	<div class="min-h-0 flex-1">
		{@render children()}
	</div>
</div>
