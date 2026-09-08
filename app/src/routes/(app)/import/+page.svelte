<script lang="ts">
	/**
	 * Importar una lista de restaurantes desde un archivo (F2.G).
	 *
	 * Tres momentos en una sola pantalla: elegir el archivo, esperar a que el
	 * servidor lo resuelva, y confirmar qué se guarda. **La confirmación no es
	 * un paso de más**: el match por nombre acierta alto pero no perfecto, y un
	 * import a ciegas llena la cuenta de alguien con restaurantes equivocados.
	 *
	 * Lo que no se pudo resolver se muestra igual. Si el archivo tenía 50 y
	 * entran 47, la persona tiene que ver cuáles tres faltaron y por qué; una
	 * pantalla que dice "listo" escondiendo tres fallas es peor que una que las
	 * enumera.
	 */
	import { goto } from '$app/navigation';
	import { t } from '$lib/i18n/index.svelte';
	import {
		importsService,
		resolvedRows,
		unresolvedRows,
		type ImportJob
	} from '$lib/services/imports.service';
	import { logSilent } from '$lib/utils/logger';
	import { SvelteSet } from 'svelte/reactivity';

	let job = $state<ImportJob | null>(null);
	let subiendo = $state(false);
	let error = $state('');
	let confirmados = $state<number>(0);
	let elegidos = $state<Set<number>>(new SvelteSet());

	const resueltas = $derived(job ? resolvedRows(job) : []);
	const sinResolver = $derived(job ? unresolvedRows(job) : []);
	const esperando = $derived(job?.state === 'pending' || job?.state === 'processing');

	let sondeo: ReturnType<typeof setInterval> | undefined;

	$effect(() => {
		// El matcheo lo hace el cron, así que hay que preguntar. Se corta solo
		// cuando el job sale de la espera: un intervalo que sigue corriendo con
		// la pantalla abierta es una request por segundo para siempre.
		if (!esperando || !job) return;
		const id = job.id;
		sondeo = setInterval(async () => {
			try {
				job = await importsService.get(id);
			} catch (err) {
				logSilent('import:poll', err);
			}
		}, 4000);
		return () => clearInterval(sondeo);
	});

	async function elegirArchivo(event: Event) {
		const input = event.target as HTMLInputElement;
		const archivo = input.files?.[0];
		if (!archivo) return;

		subiendo = true;
		error = '';
		try {
			job = await importsService.upload(archivo);
			elegidos = new SvelteSet();
		} catch (err) {
			logSilent('import:upload', err);
			error = (err as { data?: { detail?: string } })?.data?.detail || t('import.uploadFailed');
		} finally {
			subiendo = false;
			// Sin esto, elegir el mismo archivo dos veces seguidas no dispara
			// el evento y parece que la pantalla se colgó.
			input.value = '';
		}
	}

	function alternar(id: number) {
		const copia = new SvelteSet(elegidos);
		if (copia.has(id)) copia.delete(id);
		else copia.add(id);
		elegidos = copia;
	}

	function todos() {
		elegidos = new SvelteSet(resueltas.map((r) => r.restaurantId as number));
	}

	async function confirmar() {
		if (!job || elegidos.size === 0) return;
		subiendo = true;
		try {
			const res = await importsService.confirm(job.id, [...elegidos]);
			confirmados = res.created;
			job = { ...job, state: 'confirmed' };
		} catch (err) {
			logSilent('import:confirm', err);
			error = t('import.confirmFailed');
		} finally {
			subiendo = false;
		}
	}

	const MOTIVOS: Record<string, string> = {
		not_found: 'import.reasonNotFound',
		ambiguous: 'import.reasonAmbiguous',
		error: 'import.reasonError',
		unreadable: 'import.reasonUnreadable'
	};
</script>

<div class="flex h-full flex-col">
	<header class="flex shrink-0 items-center gap-3 px-4 py-3">
		<button
			onclick={() => (history.length > 1 ? history.back() : goto('/profile'))}
			class="flex min-h-11 min-w-11 items-center justify-center rounded-lg active:scale-95"
			aria-label={t('common.back')}
		>
			<svg
				class="h-6 w-6 text-ink"
				viewBox="0 0 24 24"
				fill="none"
				stroke="currentColor"
				stroke-width="2"
				stroke-linecap="round"
				stroke-linejoin="round"
			>
				<polyline points="15 18 9 12 15 6" />
			</svg>
		</button>
		<h1 class="text-lg font-semibold text-ink">{t('import.title')}</h1>
	</header>

	<main class="flex-1 overflow-y-auto px-5 pb-8">
		{#if error}
			<div
				data-testid="import-error"
				class="mb-4 rounded-button bg-blush-light/20 px-4 py-3 text-sm text-blush"
			>
				{error}
			</div>
		{/if}

		{#if !job}
			<p class="text-sm leading-relaxed text-ink-muted">{t('import.intro')}</p>

			<label
				class="mt-6 flex min-h-11 w-full cursor-pointer items-center justify-center rounded-button bg-jade px-6 font-medium text-white active:scale-95"
			>
				{subiendo ? t('import.uploading') : t('import.choose')}
				<input
					type="file"
					accept=".csv,.xlsx"
					class="hidden"
					onchange={elegirArchivo}
					disabled={subiendo}
				/>
			</label>

			<p class="mt-3 text-xs text-ink-muted">{t('import.formats')}</p>
		{:else if esperando}
			<div class="py-10 text-center" data-testid="import-waiting">
				<p class="text-sm text-ink">{t('import.working', { total: String(job.total) })}</p>
				<p class="mt-2 text-xs text-ink-muted">{t('import.workingHint')}</p>
			</div>
		{:else if job.state === 'confirmed'}
			<div class="py-10 text-center" data-testid="import-done">
				<p class="text-base font-medium text-ink">
					{t('import.done', { count: String(confirmados) })}
				</p>
				<button
					onclick={() => goto('/profile')}
					class="mt-6 min-h-11 rounded-button bg-jade px-6 font-medium text-white active:scale-95"
				>
					{t('import.seeList')}
				</button>
			</div>
		{:else}
			<div class="flex items-center justify-between">
				<p class="text-sm text-ink">
					{t('import.found', {
						matched: String(resueltas.length),
						total: String(job.total)
					})}
				</p>
				<button onclick={todos} class="min-h-11 text-sm font-medium text-jade active:opacity-70">
					{t('import.selectAll')}
				</button>
			</div>

			<ul class="mt-3 space-y-2" data-testid="import-rows">
				{#each resueltas as fila (fila.restaurantId)}
					<li>
						<label
							class="flex min-h-11 items-center gap-3 rounded-card bg-white px-4 py-3 shadow-card active:opacity-80"
						>
							<input
								type="checkbox"
								class="h-4 w-4 accent-jade"
								checked={elegidos.has(fila.restaurantId as number)}
								onchange={() => alternar(fila.restaurantId as number)}
							/>
							<span class="flex-1 text-sm text-ink">{fila.name}</span>
							{#if fila.city}
								<span class="text-xs text-ink-muted">{fila.city}</span>
							{/if}
						</label>
					</li>
				{/each}
			</ul>

			{#if sinResolver.length}
				<h2 class="mt-8 text-sm font-semibold uppercase tracking-wide text-ink-muted">
					{t('import.notFoundTitle', { count: String(sinResolver.length) })}
				</h2>
				<ul class="mt-2 space-y-1" data-testid="import-unresolved">
					{#each sinResolver as fila (fila.row)}
						<li class="flex items-baseline gap-2 px-1 text-sm text-ink-muted">
							<span class="flex-1">{fila.name || t('import.emptyRow')}</span>
							<span class="text-xs">{t(MOTIVOS[fila.outcome] ?? 'import.reasonError')}</span>
						</li>
					{/each}
				</ul>
			{/if}

			<button
				onclick={confirmar}
				disabled={elegidos.size === 0 || subiendo}
				class="mt-8 flex min-h-11 w-full items-center justify-center rounded-button bg-jade px-6 font-medium text-white active:scale-95 disabled:opacity-40"
			>
				{t('import.confirm', { count: String(elegidos.size) })}
			</button>
		{/if}
	</main>
</div>
