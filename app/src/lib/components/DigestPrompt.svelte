<script lang="ts">
	/**
	 * Ofrece el resumen diario, una sola vez.
	 *
	 * El resumen es actividad de terceros empujada al teléfono —no algo que
	 * pasó con tu cuenta—, así que desde el 2026-09-08 nace apagado y se pide.
	 * Este diálogo es ese pedido.
	 *
	 * Aparece cuando la persona tiene al menos un amigo, y no antes: el resumen
	 * es de lo que guardan tus amigos, así que ofrecerlo en el alta es ofrecer
	 * el resumen de nadie. Ese mismo criterio hace que a quien ya tenía cuenta
	 * le aparezca al abrir la app: sus amigos ya existen.
	 *
	 * Las dos respuestas marcan `digestPromptSeen`. Si el guardado falla no se
	 * marca nada, así que vuelve a preguntar en vez de comerse la decisión.
	 */
	import { t } from '$lib/i18n/index.svelte';
	import * as push from '$lib/services/push.service';
	import { authStore } from '$lib/stores/auth.store.svelte';
	import { logSilent } from '$lib/utils/logger';

	let saving = $state(false);
	let error = $state('');

	async function responder(quiere: boolean) {
		saving = true;
		error = '';
		try {
			await authStore.updateProfile({ notifyDailyDigest: quiere, digestPromptSeen: true });
			// Decir que sí sin el permiso del sistema no sirve de nada, y este
			// es el momento en que la persona acaba de decir que lo quiere.
			if (quiere && (await push.permissionState()) !== 'granted') {
				await push.enable();
			}
		} catch (err) {
			logSilent('digestPrompt:save', err);
			error = t('digest.promptError');
		} finally {
			saving = false;
		}
	}
</script>

<div class="fixed inset-0 z-50 flex items-end justify-center bg-black/40 sm:items-center">
	<div class="w-full max-w-sm rounded-t-card bg-white p-6 shadow-elevated sm:rounded-card">
		<h2 class="font-serif text-xl font-semibold text-ink">{t('digest.promptTitle')}</h2>
		<p class="mt-3 text-sm text-ink-light">{t('digest.promptBody')}</p>

		{#if error}
			<div
				data-testid="digest-prompt-error"
				class="mt-3 rounded-button bg-blush-light/20 px-4 py-3 text-sm text-blush"
			>
				{error}
			</div>
		{/if}

		<div class="mt-6 flex flex-col gap-2">
			<button
				type="button"
				data-testid="digest-prompt-yes"
				disabled={saving}
				onclick={() => responder(true)}
				class="min-h-11 rounded-button bg-jade px-4 text-base font-medium text-white active:scale-95 disabled:opacity-60"
			>
				{t('digest.promptYes')}
			</button>
			<button
				type="button"
				data-testid="digest-prompt-no"
				disabled={saving}
				onclick={() => responder(false)}
				class="min-h-11 rounded-button px-4 text-base text-ink-light active:opacity-70 disabled:opacity-60"
			>
				{t('digest.promptNo')}
			</button>
		</div>
	</div>
</div>
