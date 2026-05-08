<script lang="ts">
	import { goto } from '$app/navigation';
	import CityAutocomplete from '$lib/components/CityAutocomplete.svelte';
	import LanguagePicker from '$lib/components/LanguagePicker.svelte';
	import MuseLogo from '$lib/components/MuseLogo.svelte';
	import PasswordStrength from '$lib/components/PasswordStrength.svelte';
	import { t } from '$lib/i18n/index.svelte';
	import { restaurantsService } from '$lib/services/restaurants.service';
	import { authStore } from '$lib/stores/auth.store.svelte';
	import type { Cuisine } from '$lib/types';
	import { extractFirstDrfError } from '$lib/utils/api-error';

	// Step 1: account
	let displayName = $state('');
	let email = $state('');
	let password = $state('');
	let confirmPassword = $state('');
	let error = $state('');
	let submitting = $state(false);
	let showPassword = $state(false);
	let showConfirmPassword = $state(false);

	// Step 2: preferences
	let step = $state(1);
	let city = $state('');
	let dietary = $state('');
	let favouriteCuisine = $state<number | ''>('');
	let showKosherOnly = $state(false);
	let showGlutenFreeOnly = $state(false);
	let cuisines = $state<Cuisine[]>([]);
	let savingPrefs = $state(false);

	let passwordsMatch = $derived(password === confirmPassword);

	const dietaryOptions = $derived([
		{ value: '', label: t('dietary.none'), icon: '🍽' },
		{ value: 'Omnivore', label: t('dietary.omnivore'), icon: '🥩' },
		{ value: 'Vegetarian', label: t('dietary.vegetarian'), icon: '🥬' },
		{ value: 'Vegan', label: t('dietary.vegan'), icon: '🌱' },
		{ value: 'Kosher', label: t('dietary.kosher'), icon: '✡' },
		{ value: 'Gluten-free', label: t('dietary.glutenFree'), icon: '🚫' },
	]);

	async function handleRegister(e: Event) {
		e.preventDefault();
		error = '';

		if (!passwordsMatch) {
			error = t('auth.passwordsMismatch');
			return;
		}

		submitting = true;
		try {
			await authStore.register(email, password, displayName || undefined);
			try { cuisines = await restaurantsService.cuisines(); } catch {}
			step = 2;
		} catch (err) {
			error = extractFirstDrfError(err);
		} finally {
			submitting = false;
		}
	}

	async function savePreferences() {
		savingPrefs = true;
		try {
			const dietaryValue = [
				dietary,
				showKosherOnly && dietary !== 'Kosher' ? 'Kosher' : '',
				showGlutenFreeOnly && dietary !== 'Gluten-free' ? 'Gluten-free' : '',
			].filter(Boolean).join(', ');

			await authStore.updateProfile({
				city: city || undefined,
				dietary: dietaryValue || undefined,
				favouriteCuisine: favouriteCuisine || null,
			});
		} catch {
			// non-blocking
		} finally {
			savingPrefs = false;
			goto('/home');
		}
	}

	function skipPreferences() {
		goto('/home');
	}
</script>

<!-- STEP 1: Account creation -->
{#if step === 1}
	<div class="flex h-full flex-col items-center justify-center bg-cream px-6">
		<div class="w-full max-w-sm">
			<div class="mb-2 flex justify-center">
				<MuseLogo width={120} />
			</div>
			<h1 class="mb-1 text-center font-serif text-3xl font-bold text-jade-dark">Muse</h1>
			<p class="mb-8 text-center text-sm text-ink-muted">{t('register.subtitle')}</p>

			<form onsubmit={handleRegister} class="space-y-4">
				{#if error}
					<div class="rounded-button bg-blush-light/20 px-4 py-3 text-sm text-blush">
						{error}
					</div>
				{/if}

				<div>
					<label for="displayName" class="mb-1 block text-sm font-medium text-ink-light">{t('auth.displayName')}</label>
					<input
						id="displayName"
						type="text"
						bind:value={displayName}
						autocomplete="name"
						class="w-full rounded-input border border-cream-dark bg-white px-4 py-3 text-base text-ink outline-none transition-colors focus:border-jade"
						placeholder={t('auth.displayNamePlaceholder')}
					/>
				</div>

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
					<label for="password" class="mb-1 block text-sm font-medium text-ink-light">{t('auth.password')}</label>
					<div class="relative">
						<input
							id="password"
							type={showPassword ? 'text' : 'password'}
							bind:value={password}
							required
							minlength="8"
							autocomplete="new-password"
							class="w-full rounded-input border border-cream-dark bg-white px-4 py-3 pr-12 text-base text-ink outline-none transition-colors focus:border-jade"
							placeholder={t('auth.passwordPlaceholder')}
						/>
						<button
							type="button"
							onclick={() => (showPassword = !showPassword)}
							class="absolute right-3 top-1/2 -translate-y-1/2 p-1 text-ink-muted active:text-ink"
							aria-label={showPassword ? t('login.hidePassword') : t('login.showPassword')}
						>
							{#if showPassword}
								<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94"/><path d="M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19"/><line x1="1" y1="1" x2="23" y2="23"/></svg>
							{:else}
								<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>
							{/if}
						</button>
					</div>
					<PasswordStrength {password} />
				</div>

				<div>
					<label for="confirmPassword" class="mb-1 block text-sm font-medium text-ink-light">{t('auth.confirmPassword')}</label>
					<div class="relative">
						<input
							id="confirmPassword"
							type={showConfirmPassword ? 'text' : 'password'}
							bind:value={confirmPassword}
							required
							autocomplete="new-password"
							class="w-full rounded-input border border-cream-dark bg-white px-4 py-3 pr-12 text-base text-ink outline-none transition-colors focus:border-jade"
							placeholder={t('auth.repeatPassword')}
						/>
						<button
							type="button"
							onclick={() => (showConfirmPassword = !showConfirmPassword)}
							class="absolute right-3 top-1/2 -translate-y-1/2 p-1 text-ink-muted active:text-ink"
							aria-label={showConfirmPassword ? t('login.hidePassword') : t('login.showPassword')}
						>
							{#if showConfirmPassword}
								<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94"/><path d="M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19"/><line x1="1" y1="1" x2="23" y2="23"/></svg>
							{:else}
								<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>
							{/if}
						</button>
					</div>
				</div>

				<button
					type="submit"
					disabled={submitting || !email || !password || !confirmPassword}
					class="flex min-h-12 w-full items-center justify-center rounded-button bg-jade text-base font-semibold text-white transition-opacity active:scale-[0.98] disabled:opacity-50"
				>
					{submitting ? t('auth.creatingAccount') : t('auth.createAccount')}
				</button>
			</form>

			<p class="mt-8 text-center text-sm text-ink-muted">
				{t('auth.haveAccount')}
				<a href="/login" class="font-medium text-jade">{t('register.signInLink')}</a>
			</p>
		</div>
	</div>

<!-- STEP 2: Preferences (onboarding) -->
{:else}
	<div class="flex h-full flex-col bg-cream">
		<div class="flex-1 overflow-y-auto px-6 pb-4 pt-8">
			<div class="mx-auto w-full max-w-sm">
				<h1 class="mb-1 text-center font-serif text-2xl font-bold text-ink">{t('onboarding.welcome', { name: displayName || 'foodie' })}</h1>
				<p class="mb-6 text-center text-sm text-ink-muted">{t('onboarding.subtitle')}</p>

				<div class="space-y-5">
					<!-- Language -->
					<div>
						<p class="mb-2 text-sm font-medium text-ink-light">{t('onboarding.language')}</p>
						<LanguagePicker />
						<p class="mt-1.5 text-center text-xs text-ink-muted">{t('onboarding.languageNote')}</p>
					</div>

					<!-- City -->
					<div>
						<label for="city" class="mb-1 block text-sm font-medium text-ink-light">{t('onboarding.city')}</label>
						<CityAutocomplete bind:value={city} placeholder={t('onboarding.cityPlaceholder')} id="city" />
					</div>

					<!-- Dietary -->
					<div>
						<p class="mb-2 text-sm font-medium text-ink-light">{t('onboarding.howEat')}</p>
						<div class="grid grid-cols-3 gap-2">
							{#each dietaryOptions as opt}
								<button
									type="button"
									onclick={() => (dietary = dietary === opt.value ? '' : opt.value)}
									class="flex flex-col items-center gap-1 rounded-card p-3 text-center active:scale-95
										{dietary === opt.value ? 'bg-jade text-white shadow-card' : 'bg-white text-ink shadow-card'}"
								>
									<span class="text-lg">{opt.icon}</span>
									<span class="text-xs font-medium">{opt.label}</span>
								</button>
							{/each}
						</div>
					</div>

					<!-- Special preferences -->
					<div class="space-y-3">
						<p class="text-sm font-medium text-ink-light">{t('onboarding.specialPrefs')}</p>

						<label class="flex items-center gap-3 rounded-card bg-white p-3 shadow-card active:scale-[0.98]">
							<div class="flex h-8 w-8 items-center justify-center rounded-full bg-blue-50 text-sm">✡</div>
							<span class="flex-1 text-sm font-medium text-ink">{t('onboarding.showKosher')}</span>
							<input type="checkbox" bind:checked={showKosherOnly} class="h-5 w-5 accent-jade" />
						</label>

						<label class="flex items-center gap-3 rounded-card bg-white p-3 shadow-card active:scale-[0.98]">
							<div class="flex h-8 w-8 items-center justify-center rounded-full bg-amber-50 text-sm">🌾</div>
							<span class="flex-1 text-sm font-medium text-ink">{t('onboarding.showGlutenFree')}</span>
							<input type="checkbox" bind:checked={showGlutenFreeOnly} class="h-5 w-5 accent-jade" />
						</label>
					</div>

					<!-- Favourite cuisine -->
					<div>
						<label for="favCuisine" class="mb-1 block text-sm font-medium text-ink-light">{t('onboarding.favCuisine')}</label>
						<select
							id="favCuisine"
							bind:value={favouriteCuisine}
							class="w-full rounded-input border border-cream-dark bg-white px-4 py-3 text-base text-ink outline-none focus:border-jade"
						>
							<option value="">{t('onboarding.noPreference')}</option>
							{#each cuisines as c}
								<option value={c.id}>{c.name}</option>
							{/each}
						</select>
					</div>
				</div>
			</div>
		</div>

		<!-- Sticky action buttons -->
		<div class="shrink-0 flex gap-3 border-t border-cream-dark px-6 py-4">
			<button
				onclick={skipPreferences}
				class="flex min-h-12 flex-1 items-center justify-center rounded-button border border-cream-dark text-base font-medium text-ink-muted active:scale-[0.98]"
			>
				{t('onboarding.skip')}
			</button>
			<button
				onclick={savePreferences}
				disabled={savingPrefs}
				class="flex min-h-12 flex-1 items-center justify-center rounded-button bg-jade text-base font-semibold text-white active:scale-[0.98] disabled:opacity-50"
			>
				{savingPrefs ? t('onboarding.saving') : t('onboarding.continue')}
			</button>
		</div>
	</div>
{/if}
