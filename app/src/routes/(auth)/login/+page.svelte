<script lang="ts">
	import { goto } from '$app/navigation';
	import ForgotPasswordModal from '$lib/components/ForgotPasswordModal.svelte';
	import MuseLogo from '$lib/components/MuseLogo.svelte';
	import PasswordInput from '$lib/components/PasswordInput.svelte';
	import { t } from '$lib/i18n/index.svelte';
	import { authStore } from '$lib/stores/auth.store.svelte';
	import { ApiError } from '$lib/types';

	let email = $state('');
	let password = $state('');
	let error = $state('');
	let submitting = $state(false);
	let showForgotModal = $state(false);

	async function handleSubmit(e: Event) {
		e.preventDefault();
		error = '';
		submitting = true;

		try {
			await authStore.login(email, password);
			goto('/home');
		} catch (err) {
			if (err instanceof ApiError) {
				error = err.status === 401
					? t('auth.invalidCredentials')
					: t('common.error');
			} else {
				error = t('auth.connectionError');
			}
		} finally {
			submitting = false;
		}
	}
</script>

<div class="flex h-full flex-col items-center justify-center bg-cream px-6">
	<div class="w-full max-w-sm">
		<div class="mb-2 flex justify-center">
			<MuseLogo width={120} />
		</div>
		<h1 class="mb-1 text-center font-serif text-3xl font-bold text-jade-dark">Muse</h1>
		<p class="mb-8 text-center text-sm text-ink-muted">{t('login.subtitle')}</p>

		<form onsubmit={handleSubmit} class="space-y-4">
			{#if error}
				<div class="rounded-button bg-blush-light/20 px-4 py-3 text-sm text-blush">
					{error}
				</div>
			{/if}

			<div>
				<label for="email" class="mb-1 block text-sm font-medium text-ink-light">{t('auth.email')}</label>
				<input
					id="email"
					type="email"
					bind:value={email}
					required
					autocomplete="email"
					class="w-full rounded-input border border-cream-dark bg-white px-4 py-3 text-base text-ink outline-none transition-colors focus:border-jade"
					placeholder="you@example.com"
				/>
			</div>

			<div>
				<div class="mb-1 flex items-center justify-between">
					<label for="password" class="block text-sm font-medium text-ink-light">{t('auth.password')}</label>
					<button
						type="button"
						onclick={() => (showForgotModal = true)}
						class="text-xs font-medium text-jade active:opacity-70"
					>
						{t('login.forgotPassword')}
					</button>
				</div>
				<PasswordInput
					id="password"
					bind:value={password}
					required
					autocomplete="current-password"
					placeholder={t('login.passwordPlaceholder')}
				/>
			</div>

			<button
				type="submit"
				disabled={submitting || !email || !password}
				class="flex min-h-12 w-full items-center justify-center rounded-button bg-jade text-base font-semibold text-white transition-opacity active:scale-[0.98] disabled:opacity-50"
			>
				{submitting ? t('auth.signingIn') : t('auth.signIn')}
			</button>
		</form>

		<p class="mt-8 text-center text-sm text-ink-muted">
			{t('auth.noAccount')}
			<a href="/register" class="font-medium text-jade">{t('auth.createOne')}</a>
		</p>
	</div>
</div>

<!-- Recuperación de contraseña: email → código → contraseña nueva (RF16).
     Antes esto era un cartel que decía "viene pronto" y pedía escribir a
     soporte; la única salida real era un changepassword por SSH. -->
{#if showForgotModal}
	<ForgotPasswordModal onclose={() => (showForgotModal = false)} />
{/if}
