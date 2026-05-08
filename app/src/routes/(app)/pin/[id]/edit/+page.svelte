<script lang="ts">
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import PersonaChips from '$lib/components/PersonaChips.svelte';
	import RatingStars from '$lib/components/RatingStars.svelte';
	import StatusToggle from '$lib/components/StatusToggle.svelte';
	import { t } from '$lib/i18n/index.svelte';
	import { pinsService } from '$lib/services/pins.service';
	import type { Persona, Pin, PinStatus } from '$lib/types';
	import { extractFirstDrfError } from '$lib/utils/api-error';

	const pinId = $derived(Number(page.params.id));

	let pin = $state<Pin | null>(null);
	let loading = $state(true);
	let loadError = $state('');

	let status = $state<PinStatus>('visited');
	let rating = $state(0);
	let comment = $state('');
	let selectedPersonas = $state<number[]>([]);

	let personas = $state<Persona[]>([]);

	let saving = $state(false);
	let deleting = $state(false);
	let confirmDelete = $state(false);
	let error = $state('');

	$effect(() => {
		if (!pinId) return;
		loadPin();
		loadPersonas();
	});

	async function loadPin() {
		loading = true;
		loadError = '';
		try {
			const p = await pinsService.get(pinId);
			pin = p;
			status = p.status;
			rating = p.rating ?? 0;
			comment = p.comment ?? '';
			selectedPersonas = (p.personasDetail ?? []).map((per) => per.id);
		} catch {
			loadError = t('pin.cantLoad');
		} finally {
			loading = false;
		}
	}

	async function loadPersonas() {
		try {
			personas = await pinsService.personas();
		} catch {
			personas = [];
		}
	}

	async function handleSave() {
		if (!pin) return;
		saving = true;
		error = '';
		try {
			await pinsService.update(pin.id, {
				status,
				rating: status === 'visited' ? rating : undefined,
				comment: comment || '',
				personaIds: selectedPersonas,
			});
			goto(`/restaurant/${pin.restaurant}`);
		} catch (err) {
			error = extractFirstDrfError(err);
		} finally {
			saving = false;
		}
	}

	async function handleDelete() {
		if (!pin) return;
		deleting = true;
		try {
			await pinsService.delete(pin.id);
			goto('/profile');
		} catch (err) {
			error = extractFirstDrfError(err);
			deleting = false;
		}
	}

	function goBack() {
		history.back();
	}
</script>

<div class="flex h-full flex-col bg-cream">
	<header class="flex shrink-0 items-center gap-3 px-4 py-3">
		<button
			onclick={goBack}
			class="flex min-h-11 min-w-11 items-center justify-center rounded-lg active:scale-95"
			aria-label={t('common.back')}
		>
			<svg class="h-6 w-6 text-ink" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
				<polyline points="15 18 9 12 15 6" />
			</svg>
		</button>
		<h1 class="text-lg font-semibold text-ink">{t('pin.editPin')}</h1>
	</header>

	<main class="flex-1 overflow-y-auto px-5 pb-8">
		{#if loading}
			<div class="flex items-center justify-center py-12">
				<div class="h-7 w-7 animate-spin rounded-full border-2 border-jade border-t-transparent"></div>
			</div>
		{:else if loadError}
			<div class="rounded-card bg-blush/20 p-4 text-sm text-blush">{loadError}</div>
		{:else if pin}
			<div class="space-y-6">
				{#if error}
					<div class="rounded-card bg-blush/20 p-4 text-sm text-blush">{error}</div>
				{/if}

				<div class="rounded-card bg-white p-4 shadow-card">
					<h3 class="font-serif text-lg font-semibold text-ink">{pin.restaurantDetail?.name}</h3>
					{#if pin.restaurantDetail?.city}
						<p class="text-sm text-ink-muted">{pin.restaurantDetail.city}</p>
					{/if}
				</div>

				<div>
					<span class="mb-2 block text-sm font-medium text-ink-light">{t('pin.status')}</span>
					<StatusToggle bind:value={status} />
				</div>

				{#if status === 'visited'}
					<div>
						<span class="mb-2 block text-sm font-medium text-ink-light">{t('pin.rating')}</span>
						<RatingStars bind:value={rating} />
					</div>
				{/if}

				<div>
					<label for="comment" class="mb-1 block text-sm font-medium text-ink-light">{t('pin.myNotes')}</label>
					<textarea
						id="comment"
						bind:value={comment}
						rows="3"
						class="w-full rounded-input border border-cream-dark bg-white px-4 py-3 text-base text-ink outline-none focus:border-jade"
						placeholder={status === 'visited' ? t('pin.shareExperience') : t('pin.whyVisit')}
					></textarea>
				</div>

				{#if personas.length > 0}
					<div>
						<span class="mb-2 block text-sm font-medium text-ink-light">{t('pin.occasion')}</span>
						<PersonaChips {personas} bind:selected={selectedPersonas} />
					</div>
				{/if}

				<button
					onclick={handleSave}
					disabled={saving || (status === 'visited' && rating === 0)}
					class="flex min-h-12 w-full items-center justify-center rounded-button bg-jade text-base font-semibold text-white active:scale-[0.98] disabled:opacity-50"
				>
					{saving ? t('pin.saving') : t('pin.saveChanges')}
				</button>

				{#if !confirmDelete}
					<button
						onclick={() => (confirmDelete = true)}
						class="flex min-h-12 w-full items-center justify-center rounded-button border border-blush text-base font-medium text-blush active:scale-[0.98]"
					>
						{t('pin.delete')}
					</button>
				{:else}
					<div class="rounded-card border border-blush bg-blush/10 p-4">
						<p class="mb-3 text-sm text-ink">{t('pin.confirmDelete')}</p>
						<div class="flex gap-2">
							<button
								onclick={handleDelete}
								disabled={deleting}
								class="flex-1 rounded-button bg-blush py-2 text-sm font-semibold text-white active:scale-[0.98] disabled:opacity-50"
							>
								{deleting ? t('pin.deleting') : t('pin.yesDelete')}
							</button>
							<button
								onclick={() => (confirmDelete = false)}
								class="flex-1 rounded-button border border-cream-dark py-2 text-sm font-medium text-ink active:scale-[0.98]"
							>
								{t('profile.cancel')}
							</button>
						</div>
					</div>
				{/if}
			</div>
		{/if}
	</main>
</div>
