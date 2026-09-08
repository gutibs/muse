<script lang="ts">
	import { t } from '$lib/i18n/index.svelte';
	import type { PlaceSuggestion } from '$lib/services/places.service';

	/**
	 * Sugerencias de Google que todavía no están en el catálogo.
	 *
	 * Existe porque el bloque estaba copiado en `search` y en `pin/new` —el
	 * mismo `<path>` del pin de mapa pegado dos veces— y porque las dos
	 * pantallas se comían el fallo de Google en silencio: la llamada va en un
	 * `Promise.allSettled`, la rama rejected se descartaba sin log ni aviso, y
	 * el usuario leía "sin resultados" con Google caído. `failed` es lo que
	 * distingue "no hay" de "no pudimos preguntar".
	 */
	interface Props {
		results: PlaceSuggestion[];
		failed: boolean;
		messageKey: string | null;
		title: string;
		/** Ocupa el alto disponible: para cuando el aviso es lo único en pantalla. */
		centered?: boolean;
		importingPlaceId?: string | null;
		onselect?: (place: PlaceSuggestion) => void;
	}

	let {
		results,
		failed,
		messageKey,
		title,
		centered = false,
		importingPlaceId = null,
		onselect,
	}: Props = $props();
</script>

{#if results.length > 0}
	<section>
		<p class="mb-2 text-xs font-semibold uppercase tracking-wide text-ink-muted">{title}</p>
		<ul class="space-y-2">
			{#each results as place (place.placeId)}
				<li>
					<button
						type="button"
						onclick={() => onselect?.(place)}
						disabled={importingPlaceId !== null}
						class="flex min-h-11 w-full items-center gap-3 rounded-card bg-white p-4 text-left shadow-card active:scale-[0.98] disabled:opacity-50"
					>
						<div class="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-amber-50 text-amber-700">
							{#if importingPlaceId === place.placeId}
								<div class="h-4 w-4 animate-spin rounded-full border-2 border-amber-700 border-t-transparent"></div>
							{:else}
								<svg class="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
									<path d="M12 13a3 3 0 1 0 0-6 3 3 0 0 0 0 6Z" />
									<path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7Z" />
								</svg>
							{/if}
						</div>
						<div class="min-w-0 flex-1">
							<div class="truncate text-sm font-semibold text-ink">{place.name}</div>
							<div class="truncate text-xs text-ink-muted">{place.address}</div>
						</div>
					</button>
				</li>
			{/each}
		</ul>
	</section>
{/if}

{#if failed}
	<p
		role="status"
		class="text-center text-sm text-ink-muted {centered
			? 'flex h-full flex-col items-center justify-center px-8'
			: 'py-4'}"
	>
		{t(messageKey ?? 'common.networkError')}
	</p>
{/if}
