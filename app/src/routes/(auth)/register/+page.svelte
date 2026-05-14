<script lang="ts">
	import { goto } from '$app/navigation';
	import CityAutocomplete from '$lib/components/CityAutocomplete.svelte';
	import LanguagePicker from '$lib/components/LanguagePicker.svelte';
	import MuseLogo from '$lib/components/MuseLogo.svelte';
	import PasswordStrength from '$lib/components/PasswordStrength.svelte';
	import { t } from '$lib/i18n/index.svelte';
	import { authService } from '$lib/services/auth.service';
	import { restaurantsService } from '$lib/services/restaurants.service';
	import { authStore } from '$lib/stores/auth.store.svelte';
	import type { Cuisine, DietaryPreference } from '$lib/types';
	import { extractFirstDrfError } from '$lib/utils/api-error';
	import { logSilent } from '$lib/utils/logger';

	// Frontend-only icon map per dietary preference slug. The backend doesn't
	// know about icons (DietaryPreference has only name + slug), so this small
	// presentation-layer table stays here. Slugs are stable (set by migration).
	const DIETARY_ICONS: Record<string, string> = {
		omnivore: '🥩',
		vegetarian: '🥬',
		vegan: '🌱',
		kosher: '✡',
		'gluten-free': '🌾',
	};

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
	let dietaryIds = $state<number[]>([]);
	let favouriteCuisine = $state<number | ''>('');
	let cuisines = $state<Cuisine[]>([]);
	let dietaryOptions = $state<DietaryPreference[]>([]);
	let savingPrefs = $state(false);

	let passwordsMatch = $derived(password === confirmPassword);

	function toggleDietary(id: number) {
		dietaryIds = dietaryIds.includes(id)
			? dietaryIds.filter((x) => x !== id)
			: [...dietaryIds, id];
	}

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
			// Both lookups are non-blocking — the user can finish registration
			// even if either list fails to load (UI just renders empty grids).
			try {
				cuisines = await restaurantsService.cuisines();
			} catch (err) {
				logSilent('register.loadCuisines', err);
			}
			try {
				dietaryOptions = await authService.dietaryPreferences();
			} catch (err) {
				logSilent('register.loadDietaryOptions', err);
			}
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
			await authStore.updateProfile({
				city: city || undefined,
				dietaryPreferences: dietaryIds,
				favouriteCuisine: favouriteCuisine || null,
			});
		} catch (err) {
			logSilent('register.savePreferences', err);
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
	<div class="relative flex h-full flex-col items-center justify-center bg-cream px-6">
		<a
			href="/login"
			aria-label={t('common.back')}
			class="absolute left-3 top-3 flex min-h-11 min-w-11 items-center justify-center rounded-full text-ink-light active:bg-cream-dark active:opacity-70"
			style="top: calc(env(safe-area-inset-top, 0px) + 0.5rem);"
		>
			<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M19 12H5"/><path d="M12 19l-7-7 7-7"/></svg>
		</a>
		<div class="w-full max-w-sm">
			<div class="mb-2 flex justify-center">
				<MuseLogo width={120} href="/login" />
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

					<!-- Dietary preferences (multi-select chips). Replaces single
						 select + 2 checkboxes; the underlying model is a M2M now,
						 so Kosher/Gluten-free combine naturally with Vegan etc. -->
					<div>
						<p class="mb-2 text-sm font-medium text-ink-light">{t('onboarding.howEat')}</p>
						<div class="grid grid-cols-3 gap-2">
							{#each dietaryOptions as opt (opt.id)}
								{@const selected = dietaryIds.includes(opt.id)}
								<button
									type="button"
									onclick={() => toggleDietary(opt.id)}
									class="flex flex-col items-center gap-1 rounded-card p-3 text-center active:scale-95
										{selected ? 'bg-jade text-white shadow-card' : 'bg-white text-ink shadow-card'}"
									aria-pressed={selected}
								>
									<span class="text-lg">{DIETARY_ICONS[opt.slug] ?? '🍽'}</span>
									<span class="text-xs font-medium">{opt.name}</span>
								</button>
							{/each}
						</div>
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
