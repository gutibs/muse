<script lang="ts">
	/**
	 * Una lista compartida en el perfil de su dueño: el link, copiarlo,
	 * borrarla y —sólo si es curada— el interruptor de votación.
	 *
	 * Existe como componente y no suelto en `profile/+page.svelte` porque el
	 * interruptor tiene estado optimista con vuelta atrás, y esa lógica se
	 * testea por el borde que toca una persona.
	 */
	import { t } from '$lib/i18n/index.svelte';
	import { logSilent } from '$lib/utils/logger';

	export type ShareRow = {
		id: number;
		title: string;
		url: string;
		kind: string;
		votingEnabled: boolean;
	};

	let {
		list,
		onCopy,
		onRemove,
		onToggleVoting,
	}: {
		list: ShareRow;
		onCopy: (url: string) => void;
		onRemove: (id: number) => void;
		onToggleVoting: (id: number, enabled: boolean) => Promise<void>;
	} = $props();

	/**
	 * Lo que dijimos mientras el servidor no contesta. `list` es la verdad:
	 * copiarla a un `$state` capturaría sólo el valor inicial y la fila
	 * quedaría mostrando lo de antes tras recargar la pantalla.
	 */
	let optimista = $state<boolean | null>(null);
	let enVuelo = $state(false);

	const votando = $derived(
		optimista === null || optimista === list.votingEnabled ? list.votingEnabled : optimista
	);

	async function alternar() {
		if (enVuelo) return;
		const nuevo = !votando;
		optimista = nuevo;
		enVuelo = true;
		try {
			await onToggleVoting(list.id, nuevo);
		} catch (err) {
			optimista = null;
			logSilent('profile.toggleVoting', err);
		} finally {
			enVuelo = false;
		}
	}
</script>

<li class="rounded-card bg-white p-4 shadow-card">
	<div class="flex items-center gap-3">
		<div class="min-w-0 flex-1">
			<p class="truncate text-sm font-medium text-ink">{list.title || t('profile.myList')}</p>
			<p class="truncate text-xs text-ink-muted">{list.url}</p>
		</div>
		<button
			onclick={() => onCopy(list.url)}
			class="flex min-h-9 items-center rounded-button bg-jade/10 px-3 text-xs font-semibold text-jade active:scale-[0.98]"
		>
			{t('profile.copy')}
		</button>
		<button
			onclick={() => onRemove(list.id)}
			class="flex min-h-9 items-center rounded-button border border-cream-dark px-3 text-xs font-medium text-ink-muted active:scale-[0.98]"
		>
			{t('profile.remove')}
		</button>
	</div>

	<!-- Sólo en listas curadas: una `auto` no tiene items elegidos a mano, así
	     que no hay sobre qué votar y el backend la rechaza igual. -->
	{#if list.kind === 'curated'}
		<label class="mt-3 flex min-h-11 items-start gap-3 border-t border-cream pt-3">
			<input
				type="checkbox"
				checked={votando}
				onchange={alternar}
				aria-label={t('vote.enable')}
				class="mt-0.5 h-5 w-5 shrink-0 accent-jade"
			/>
			<span class="min-w-0 flex-1">
				<span class="block text-sm text-ink">{t('vote.enable')}</span>
				<span class="block text-xs text-ink-muted">{t('vote.enableHint')}</span>
			</span>
		</label>
	{/if}
</li>
