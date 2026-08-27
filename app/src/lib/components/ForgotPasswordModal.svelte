<script lang="ts">
	import { i18n, t } from '$lib/i18n/index.svelte';
	import { passwordResetService } from '$lib/services/password-reset.service';
	import { logSilent } from '$lib/utils/logger';
	import { ApiError } from '$lib/types';

	let { onclose }: { onclose: () => void } = $props();

	type Step = 'email' | 'code' | 'password' | 'done';

	let step = $state<Step>('email');
	let email = $state('');
	let code = $state('');
	let newPassword = $state('');
	let error = $state('');
	let submitting = $state(false);

	/** El backend responde 200 exista o no la cuenta. La app avanza igual: si
	 * se quedara en el paso 1 para los emails sin cuenta, reintroduciría por
	 * la UI el oráculo de enumeración que el backend cierra. */
	async function askForCode(e?: Event) {
		e?.preventDefault();
		error = '';
		submitting = true;
		try {
			await passwordResetService.requestCode(email, i18n.locale);
			step = 'code';
		} catch (err) {
			logSilent('forgot-password:request', err);
			error = t('auth.connectionError');
		} finally {
			submitting = false;
		}
	}

	function goToPassword(e: Event) {
		e.preventDefault();
		error = '';
		step = 'password';
	}

	async function submitNewPassword(e: Event) {
		e.preventDefault();
		error = '';
		submitting = true;
		try {
			await passwordResetService.confirm(email, code, newPassword, i18n.locale);
			step = 'done';
		} catch (err) {
			logSilent('forgot-password:confirm', err);
			if (err instanceof ApiError && err.status === 400) {
				// El backend no distingue código errado, vencido, quemado ni
				// usado — a propósito, todos llegan bajo la clave `code`. Los
				// errores de contraseña vienen aparte y ya traducidos, así que
				// son los únicos que se muestran literales.
				const data = err.data as Record<string, string[]> | null;
				const passwordErrors = data?.newPassword;
				if (passwordErrors?.length) {
					error = passwordErrors.join(' ');
				} else {
					// Vuelve al paso del código: decir "pedí uno nuevo" en la
					// pantalla de la contraseña le pide a la persona algo que
					// desde ahí no puede hacer. El valor tipeado queda puesto
					// para corregir un dígito sin retipear los seis.
					error = t('login.resetInvalidCode');
					step = 'code';
				}
			} else {
				error = t('auth.connectionError');
			}
		} finally {
			submitting = false;
		}
	}

	const TITLES: Record<Step, string> = {
		email: 'login.forgotPassword',
		code: 'login.resetCodeStep',
		password: 'login.resetNewPasswordStep',
		done: 'login.resetDone'
	};
</script>

<!-- svelte-ignore a11y_click_events_have_key_events -->
<!-- svelte-ignore a11y_no_static_element_interactions -->
<div class="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-6" onclick={onclose}>
	<!-- svelte-ignore a11y_click_events_have_key_events -->
	<!-- svelte-ignore a11y_no_static_element_interactions -->
	<div
		class="w-full max-w-sm rounded-card bg-white p-6 shadow-elevated"
		onclick={(e) => e.stopPropagation()}
	>
		<div class="mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-jade/10 text-jade">
			<svg class="h-6 w-6" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
				<rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/>
			</svg>
		</div>
		<h2 class="font-serif text-xl font-semibold text-ink">{t(TITLES[step])}</h2>

		{#if error}
			<div data-testid="reset-error" class="mt-3 rounded-button bg-blush-light/20 px-4 py-3 text-sm text-blush">
				{error}
			</div>
		{/if}

		{#if step === 'email'}
			<p class="mt-2 text-sm text-ink-light">{t('login.forgotBody')}</p>
			<form onsubmit={askForCode} class="mt-4 space-y-3">
				<input
					type="email"
					bind:value={email}
					required
					autocomplete="email"
					placeholder="you@example.com"
					class="w-full rounded-input border border-cream-dark bg-white px-4 py-3 text-base text-ink outline-none transition-colors focus:border-jade"
				/>
				<button
					type="submit"
					disabled={submitting || !email}
					class="flex min-h-11 w-full items-center justify-center rounded-button bg-jade text-sm font-semibold text-white active:scale-[0.98] disabled:opacity-50"
				>
					{t('login.resetEmailStep')}
				</button>
			</form>
		{:else if step === 'code'}
			<p class="mt-2 text-sm text-ink-light">{t('login.resetCodeSent')}</p>
			<form onsubmit={goToPassword} class="mt-4 space-y-3">
				<label for="reset-code" class="block text-sm font-medium text-ink-light">
					{t('login.resetCodeLabel')}
				</label>
				<input
					id="reset-code"
					name="code"
					bind:value={code}
					required
					inputmode="numeric"
					autocomplete="one-time-code"
					maxlength="6"
					placeholder="000000"
					class="w-full rounded-input border border-cream-dark bg-white px-4 py-3 text-center text-2xl tracking-[0.5em] text-ink outline-none transition-colors focus:border-jade"
				/>
				<button
					type="submit"
					disabled={!code}
					class="flex min-h-11 w-full items-center justify-center rounded-button bg-jade text-sm font-semibold text-white active:scale-[0.98] disabled:opacity-50"
				>
					{t('common.continue')}
				</button>
				<button
					type="button"
					data-testid="resend-code"
					onclick={() => askForCode()}
					disabled={submitting}
					class="flex min-h-11 w-full items-center justify-center rounded-button text-sm font-medium text-jade active:opacity-70 disabled:opacity-50"
				>
					{t('login.resetResend')}
				</button>
			</form>
		{:else if step === 'password'}
			<p class="mt-2 text-sm text-ink-light">{t('login.resetOtherSessions')}</p>
			<form onsubmit={submitNewPassword} class="mt-4 space-y-3">
				<label for="reset-new-password" class="block text-sm font-medium text-ink-light">
					{t('login.resetNewPasswordLabel')}
				</label>
				<input
					id="reset-new-password"
					name="newPassword"
					type="password"
					bind:value={newPassword}
					required
					autocomplete="new-password"
					class="w-full rounded-input border border-cream-dark bg-white px-4 py-3 text-base text-ink outline-none transition-colors focus:border-jade"
				/>
				<button
					type="submit"
					disabled={submitting || !newPassword}
					class="flex min-h-11 w-full items-center justify-center rounded-button bg-jade text-sm font-semibold text-white active:scale-[0.98] disabled:opacity-50"
				>
					{t('login.resetSubmit')}
				</button>
				<button
					type="button"
					onclick={() => (step = 'code')}
					class="flex min-h-11 w-full items-center justify-center rounded-button text-sm font-medium text-jade active:opacity-70"
				>
					{t('login.resetBack')}
				</button>
			</form>
		{:else}
			<p class="mt-2 text-sm text-ink-light">{t('login.resetDoneBody')}</p>
			<button
				onclick={onclose}
				class="mt-5 flex min-h-11 w-full items-center justify-center rounded-button bg-jade text-sm font-semibold text-white active:scale-[0.98]"
			>
				{t('login.gotIt')}
			</button>
		{/if}
	</div>
</div>
