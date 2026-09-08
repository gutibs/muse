<script lang="ts">
	/**
	 * El bloque de votación de una shortlist pública.
	 *
	 * Optimista: el tick y el número se mueven al tocar y vuelven atrás si
	 * el servidor rechaza. La pantalla se abre desde un chat grupal, donde
	 * esperar el round-trip para ver el propio tick se siente roto.
	 *
	 * No sabe nada de HTTP: recibe `onVote` y avisa. Así se testea sin
	 * levantar un servidor y la página decide cómo hablar con la API.
	 */
	import { t } from '$lib/i18n/index.svelte';
	import CheckIcon from '$lib/components/CheckIcon.svelte';
	import { logSilent } from '$lib/utils/logger';
	import { SvelteMap, SvelteSet } from 'svelte/reactivity';

	export type VoteItem = {
		itemId: number;
		name: string;
		voteCount: number;
		hasVoted: boolean;
	};

	let {
		items,
		onVote,
		row,
	}: {
		items: VoteItem[];
		onVote: (itemId: number, votar: boolean) => Promise<void>;
		/**
		 * Cómo se dibuja cada fila. Sin esto sería sólo el nombre, y en la
		 * página pública la tarjeta con foto, nota y rating es justamente lo
		 * que hace falta para decidir. La lógica de voto queda acá igual.
		 */
		row?: import('svelte').Snippet<[VoteItem]>;
	} = $props();

	/**
	 * El voto propio mientras el servidor todavía no lo confirmó.
	 *
	 * No es una copia de la lista: `items` es siempre la verdad y esto sólo
	 * pisa el tick de quien está tocando. Una copia local se desincronizaba
	 * —los votos de los demás no llegaban— y sincronizarla con un `$effect`
	 * terminó en `effect_update_depth_exceeded`.
	 */
	let optimista = $state(new SvelteMap<number, boolean>());
	let enVuelo = $state(new SvelteSet<number>());

	const filas = $derived(
		items.map((item) => {
			const propio = optimista.get(item.itemId);
			// Cuando el servidor ya refleja lo que dijimos, el override sobra.
			if (propio === undefined || propio === item.hasVoted) return item;
			return {
				...item,
				hasVoted: propio,
				// Sobre el conteo del servidor, no sobre el anterior: así los
				// votos que entraron mientras tanto siguen contando.
				voteCount: item.voteCount + (propio ? 1 : -1),
			};
		})
	);

	async function alternar(item: VoteItem) {
		// Dos toques rápidos mandarían dos requests, y el rollback de una
		// pisaría el estado de la otra.
		if (enVuelo.has(item.itemId)) return;

		const votar = !item.hasVoted;
		optimista.set(item.itemId, votar);
		enVuelo.add(item.itemId);

		try {
			await onVote(item.itemId, votar);
		} catch (err) {
			optimista.delete(item.itemId);
			logSilent('vote', err);
		} finally {
			enVuelo.delete(item.itemId);
		}
	}
</script>

<ul class="flex flex-col gap-2">
	{#each filas as item (item.itemId)}
		<li class="flex items-start gap-3">
			<div class="flex w-11 shrink-0 flex-col items-center gap-1">
				<button
					type="button"
					class="flex min-h-11 min-w-11 items-center justify-center rounded-xl border-2 transition active:scale-95 {item.hasVoted
						? 'border-jade bg-jade text-white'
						: 'border-cream-dark bg-white'}"
					aria-pressed={item.hasVoted}
					aria-label={t(item.hasVoted ? 'vote.remove' : 'vote.cast').replace(
						'{name}',
						item.name
					)}
					onclick={() => alternar(item)}
				>
					<!-- Sin voto no hay glifo. Con el check dibujado en gris, un
					     botón que nadie tocó se lee como marcado: se vio en la
					     pantalla, no en los tests. Dejarlo transparente vía
					     `currentColor` no alcanzó — el trazo seguía visible. -->
					{#if item.hasVoted}<CheckIcon />{/if}
				</button>
				<span
					class="text-xs font-semibold tabular-nums {item.hasVoted
						? 'text-jade-dark'
						: 'text-ink-muted'}"
					data-testid="vote-count-{item.itemId}">{item.voteCount}</span
				>
			</div>
			<div class="min-w-0 flex-1">
				{#if row}{@render row(item)}{:else}<span class="truncate text-base text-ink"
						>{item.name}</span
					>{/if}
			</div>
		</li>
	{/each}
</ul>
