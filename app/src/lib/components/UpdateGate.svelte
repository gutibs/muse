<script lang="ts">
	import { t } from '$lib/i18n/index.svelte';
	import MuseLogo from '$lib/components/MuseLogo.svelte';
	import type { VersionCheck } from '$lib/services/version.service';

	let { check }: { check: VersionCheck } = $props();

	// La sugerencia se descarta y no vuelve en esta sesión. No se guarda en
	// storage a propósito: si la persona la descarta una vez y nunca más la ve,
	// la única forma de enterarse de una versión nueva desaparece para siempre.
	let dismissed = $state(false);
</script>

{#if check.state === 'blocked'}
	<!--
		Pantalla sin salida, y por eso va por encima de todo: si la versión
		instalada ya no habla el mismo idioma que la API, dejarla usar la app es
		peor que frenarla — falla en pantallas sueltas, sin decir por qué.

		Es el único lugar fuera de AppShell que aplica safe areas, porque se
		dibuja por encima de él y sin esto el texto queda bajo el notch.
	-->
	<div
		class="fixed inset-0 z-[100] flex h-full flex-col items-center justify-center bg-cream px-8 text-center"
		style="padding-top: var(--sat); padding-bottom: var(--sab); padding-left: var(--sal); padding-right: var(--sar);"
		data-testid="update-required"
	>
		<MuseLogo width={140} />
		<h1 class="mt-8 font-serif text-2xl font-semibold text-ink">
			{t('update.blocked.title')}
		</h1>
		<p class="mt-3 max-w-xs text-sm leading-relaxed text-ink-muted">
			{t('update.blocked.body')}
		</p>

		{#if check.storeUrl}
			<a
				href={check.storeUrl}
				class="mt-8 flex min-h-11 w-full max-w-xs items-center justify-center rounded-button bg-jade px-6 font-medium text-white active:scale-95"
			>
				{t('update.action')}
			</a>
		{:else}
			<!--
				`store_url` arranca vacío: las tiendas todavía no están aprobadas.
				Sin link no hay botón que llevar a ningún lado, pero la pantalla
				igual tiene que explicar qué hacer en vez de quedar muda.
			-->
			<p class="mt-8 max-w-xs text-sm text-ink-muted" data-testid="update-no-link">
				{t('update.blocked.noLink')}
			</p>
		{/if}
	</div>
{:else if check.state === 'outdated' && !dismissed}
	<!--
		Va arriba y no abajo: pegado al borde inferior tapaba la barra de
		navegación entera —Inicio, Feed, Muse, Buscar, Yo— y mientras el banner
		estuviera visible no se podía navegar. Se vio en el teléfono, no en el
		código: el banner vive en el layout raíz y la nav en el de `(app)`, así
		que nada en el código dice que se pisan.
	-->
	<div
		class="fixed inset-x-0 top-0 z-40 border-b border-sand bg-white px-4 py-3 shadow-elevated"
		style="padding-top: calc(var(--sat) + 0.75rem);"
		data-testid="update-available"
	>
		<div class="flex items-center gap-3">
			<p class="flex-1 text-sm text-ink">{t('update.outdated.body')}</p>
			{#if check.storeUrl}
				<a
					href={check.storeUrl}
					class="flex min-h-11 shrink-0 items-center rounded-button bg-jade px-4 text-sm font-medium text-white active:scale-95"
				>
					{t('update.action')}
				</a>
			{/if}
			<button
				type="button"
				onclick={() => (dismissed = true)}
				aria-label={t('update.dismiss')}
				class="flex min-h-11 min-w-11 shrink-0 items-center justify-center text-ink-muted active:opacity-70"
			>
				✕
			</button>
		</div>
	</div>
{/if}
