<script lang="ts">
	import { authStore } from '$lib/stores/auth.store.svelte';
	import { authService } from '$lib/services/auth.service';
	import { ApiError } from '$lib/types';

	// Change password
	let changingPassword = $state(false);
	let currentPassword = $state('');
	let newPassword = $state('');
	let confirmPassword = $state('');
	let pwError = $state('');
	let pwSuccess = $state('');
	let pwSaving = $state(false);

	function togglePasswordForm() {
		changingPassword = !changingPassword;
		currentPassword = '';
		newPassword = '';
		confirmPassword = '';
		pwError = '';
	}

	async function handleChangePassword() {
		pwError = '';

		if (newPassword !== confirmPassword) {
			pwError = 'Passwords do not match.';
			return;
		}

		pwSaving = true;
		try {
			await authService.changePassword(currentPassword, newPassword);
			pwSuccess = 'Password updated';
			changingPassword = false;
			currentPassword = '';
			newPassword = '';
			confirmPassword = '';
			setTimeout(() => (pwSuccess = ''), 3000);
		} catch (err) {
			if (err instanceof ApiError && err.data) {
				const data = err.data as Record<string, string[]>;
				const firstKey = Object.keys(data)[0];
				const messages = data[firstKey];
				pwError = Array.isArray(messages) ? messages[0] : String(messages);
			} else {
				pwError = 'Could not change password.';
			}
		} finally {
			pwSaving = false;
		}
	}
</script>

<div class="flex h-full flex-col">
	<header class="flex shrink-0 items-center gap-3 px-4 py-3">
		<a
			href="/profile"
			class="flex min-h-11 min-w-11 items-center justify-center rounded-lg active:scale-95"
			aria-label="Go back"
		>
			<svg class="h-6 w-6 text-ink" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
				<polyline points="15 18 9 12 15 6" />
			</svg>
		</a>
		<h1 class="text-lg font-semibold text-ink">Settings</h1>
	</header>

	<div class="flex-1 overflow-y-auto px-5 pb-6">
		{#if pwSuccess}
			<div class="mb-4 rounded-card bg-jade/10 px-4 py-3 text-sm font-medium text-jade">
				{pwSuccess}
			</div>
		{/if}

		<!-- Account section -->
		<section>
			<h2 class="mb-3 text-sm font-semibold uppercase tracking-wide text-ink-muted">Account</h2>
			<div class="space-y-2">
				<div class="rounded-card bg-white p-4 shadow-card">
					<div class="text-xs text-ink-muted">Email</div>
					<div class="text-sm font-medium text-ink">{authStore.user?.email}</div>
				</div>

				<button
					onclick={togglePasswordForm}
					class="flex w-full items-center justify-between rounded-card bg-white p-4 shadow-card active:scale-[0.98]"
				>
					<span class="text-sm font-medium text-ink">Change Password</span>
					<svg class="h-4 w-4 text-ink-muted transition-transform {changingPassword ? 'rotate-180' : ''}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
						<polyline points="6 9 12 15 18 9" />
					</svg>
				</button>

				{#if changingPassword}
					<div class="space-y-3 rounded-card bg-white p-4 shadow-card">
						{#if pwError}
							<div class="rounded-button bg-blush-light/20 px-3 py-2 text-sm text-blush">{pwError}</div>
						{/if}

						<div>
							<label for="currentPw" class="mb-1 block text-xs font-medium text-ink-light">Current Password</label>
							<input
								id="currentPw"
								type="password"
								bind:value={currentPassword}
								autocomplete="current-password"
								class="w-full rounded-input border border-cream-dark bg-white px-4 py-3 text-base text-ink outline-none focus:border-jade"
							/>
						</div>
						<div>
							<label for="newPw" class="mb-1 block text-xs font-medium text-ink-light">New Password</label>
							<input
								id="newPw"
								type="password"
								bind:value={newPassword}
								autocomplete="new-password"
								class="w-full rounded-input border border-cream-dark bg-white px-4 py-3 text-base text-ink outline-none focus:border-jade"
							/>
						</div>
						<div>
							<label for="confirmPw" class="mb-1 block text-xs font-medium text-ink-light">Confirm Password</label>
							<input
								id="confirmPw"
								type="password"
								bind:value={confirmPassword}
								autocomplete="new-password"
								class="w-full rounded-input border border-cream-dark bg-white px-4 py-3 text-base text-ink outline-none focus:border-jade"
							/>
						</div>
						<button
							onclick={handleChangePassword}
							disabled={pwSaving || !currentPassword || !newPassword || !confirmPassword}
							class="flex min-h-11 w-full items-center justify-center rounded-button bg-jade text-sm font-semibold text-white active:scale-[0.98] disabled:opacity-50"
						>
							{pwSaving ? 'Updating...' : 'Update Password'}
						</button>
					</div>
				{/if}
			</div>
		</section>

		<!-- About section -->
		<section class="mt-6">
			<h2 class="mb-3 text-sm font-semibold uppercase tracking-wide text-ink-muted">About</h2>
			<div class="space-y-2">
				<div class="rounded-card bg-white p-4 shadow-card">
					<div class="text-sm font-medium text-ink">Muse</div>
					<div class="text-xs text-ink-muted">Version 0.1.0 (MVP)</div>
				</div>
			</div>
		</section>

		<!-- Sign out -->
		<div class="mt-8">
			<button
				onclick={() => authStore.logout()}
				class="flex min-h-12 w-full items-center justify-center rounded-button border border-blush text-base font-medium text-blush active:scale-[0.98]"
			>
				Sign Out
			</button>
		</div>
	</div>
</div>
