<script lang="ts">
	import { goto } from '$app/navigation';
	import ForgotPasswordModal from '$lib/components/ForgotPasswordModal.svelte';
	import MuseLogo from '$lib/components/MuseLogo.svelte';
	import { t } from '$lib/i18n/index.svelte';
	import { authStore } from '$lib/stores/auth.store.svelte';
	import { ApiError } from '$lib/types';

	let email = $state('');
	let password = $state('');
	let showPassword = $state(false);
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
				<div class="relative">
					<input
						id="password"
						type={showPassword ? 'text' : 'password'}
						bind:value={password}
						required
						autocomplete="current-password"
						class="w-full rounded-input border border-cream-dark bg-white px-4 py-3 pr-12 text-base text-ink outline-none transition-colors focus:border-jade"
						placeholder={t('login.passwordPlaceholder')}
					/>
					<button
						type="button"
						onclick={() => (showPassword = !showPassword)}
						aria-label={showPassword ? t('login.hidePassword') : t('login.showPassword')}
						class="absolute right-2 top-1/2 flex h-10 w-10 -translate-y-1/2 items-center justify-center rounded-lg text-ink-muted active:scale-90"
					>
						{#if showPassword}
							<svg class="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
								<path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"/>
								<line x1="1" y1="1" x2="23" y2="23"/>
							</svg>
						{:else}
							<svg class="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
								<path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/>
							</svg>
						{/if}
					</button>
				</div>
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
