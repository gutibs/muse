<script lang="ts">
	import { t } from '$lib/i18n/index.svelte';
	import {
		moderationService,
		REPORT_REASONS,
		type ReportReason
	} from '$lib/services/moderation.service';
	import { logSilent } from '$lib/utils/logger';

	let {
		user,
		pinId,
		onclose,
		onblocked
	}: {
		user: { id: number; displayName?: string };
		pinId?: number;
		onclose: () => void;
		onblocked?: () => void;
	} = $props();

	let reason = $state<ReportReason | ''>('');
	let detail = $state('');
	let sending = $state(false);
	let sent = $state(false);
	let blocked = $state(false);
	let error = $state('');

	const name = $derived(user.displayName || t('restaurant.anonymous'));

	async function submit(e: Event) {
		e.preventDefault();
		if (!reason) return;
		error = '';
		sending = true;
		try {
			await moderationService.report({
				reportedUserId: user.id,
				reason,
				...(pinId !== undefined ? { pinId } : {}),
				...(detail.trim() ? { detail: detail.trim() } : {})
			});
			sent = true;
		} catch (err) {
			logSilent('report:submit', err);
			error = t('moderation.reportError');
		} finally {
			sending = false;
		}
	}

	/** Quien acaba de denunciar por acoso casi siempre quiere además dejar de
	 * ver a esa persona. Ofrecerlo acá evita que tenga que volver a buscarla. */
	async function blockToo() {
		try {
			await moderationService.block(user.id);
			blocked = true;
			onblocked?.();
		} catch (err) {
			logSilent('report:block-too', err);
			error = t('common.error');
		}
	}
</script>

<!-- svelte-ignore a11y_click_events_have_key_events -->
<!-- svelte-ignore a11y_no_static_element_interactions -->
<div class="fixed inset-0 z-50 flex items-end justify-center bg-black/40 sm:items-center" onclick={onclose}>
	<!-- svelte-ignore a11y_click_events_have_key_events -->
	<!-- svelte-ignore a11y_no_static_element_interactions -->
	<div
		class="w-full max-w-sm rounded-t-card bg-white p-6 shadow-elevated sm:rounded-card"
		onclick={(e) => e.stopPropagation()}
	>
		<h2 class="font-serif text-xl font-semibold text-ink">
			{pinId !== undefined
				? t('moderation.reportReview')
				: t('moderation.reportTitle').replace('{name}', name)}
		</h2>

		{#if error}
			<div data-testid="report-error" class="mt-3 rounded-button bg-blush-light/20 px-4 py-3 text-sm text-blush">
				{error}
			</div>
		{/if}

		{#if !sent}
			<form onsubmit={submit} class="mt-4 space-y-4">
				<fieldset class="space-y-2">
					{#each REPORT_REASONS as value (value)}
						<label class="flex min-h-11 items-center gap-3 rounded-button px-2 text-sm text-ink active:opacity-70">
							<input type="radio" name="reason" {value} bind:group={reason} class="h-4 w-4 accent-jade" />
							{t(`moderation.reason.${value}`)}
						</label>
					{/each}
				</fieldset>

				<label class="block text-sm text-ink-light">
					{t('moderation.reportDetail')}
					<textarea
						bind:value={detail}
						maxlength="1000"
						rows="3"
						class="mt-1 w-full rounded-input border border-cream-dark bg-white px-3 py-2 text-base text-ink outline-none focus:border-jade"
					></textarea>
				</label>

				<button
					type="submit"
					disabled={!reason || sending}
					class="flex min-h-11 w-full items-center justify-center rounded-button bg-jade text-sm font-semibold text-white active:scale-[0.98] disabled:opacity-50"
				>
					{t('moderation.reportSend')}
				</button>
			</form>
		{:else}
			<p class="mt-2 text-sm text-ink-light">{t('moderation.reportDone')}</p>
			{#if !blocked}
				<button
					type="button"
					data-testid="block-too"
					onclick={blockToo}
					class="mt-5 flex min-h-11 w-full items-center justify-center rounded-button border border-cream-dark text-sm font-semibold text-ink active:scale-[0.98]"
				>
					{t('moderation.reportBlockToo')}
				</button>
			{:else}
				<p class="mt-5 text-center text-sm font-medium text-jade">{t('moderation.blocked')}</p>
			{/if}
			<button
				type="button"
				onclick={onclose}
				class="mt-3 flex min-h-11 w-full items-center justify-center rounded-button bg-jade text-sm font-semibold text-white active:scale-[0.98]"
			>
				{t('login.gotIt')}
			</button>
		{/if}
	</div>
</div>
