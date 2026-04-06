<script lang="ts">
	import { goto } from '$app/navigation';
	import MuseLogo from '$lib/components/MuseLogo.svelte';
	import PasswordStrength from '$lib/components/PasswordStrength.svelte';
	import { authStore } from '$lib/stores/auth.store.svelte';
	import { ApiError } from '$lib/types';

	let displayName = $state('');
	let email = $state('');
	let password = $state('');
	let confirmPassword = $state('');
	let error = $state('');
	let submitting = $state(false);

	let passwordsMatch = $derived(password === confirmPassword);

	async function handleSubmit(e: Event) {
		e.preventDefault();
		error = '';

		if (!passwordsMatch) {
			error = 'Passwords do not match.';
			return;
		}

		submitting = true;

		try {
			await authStore.register(email, password, displayName || undefined);
			goto('/home');
		} catch (err) {
			if (err instanceof ApiError && err.data) {
				const data = err.data as Record<string, string[]>;
				const firstKey = Object.keys(data)[0];
				const messages = data[firstKey];
				error = Array.isArray(messages) ? messages[0] : String(messages);
			} else {
				error = 'Something went wrong. Please try again.';
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
		<p class="mb-8 text-center text-sm text-ink-muted">Create your account</p>

		<form onsubmit={handleSubmit} class="space-y-4">
			{#if error}
				<div class="rounded-button bg-blush-light/20 px-4 py-3 text-sm text-blush">
					{error}
				</div>
			{/if}

			<div>
				<label for="displayName" class="mb-1 block text-sm font-medium text-ink-light">Display Name</label>
				<input
					id="displayName"
					type="text"
					bind:value={displayName}
					autocomplete="name"
					class="w-full rounded-input border border-cream-dark bg-white px-4 py-3 text-base text-ink outline-none transition-colors focus:border-jade"
					placeholder="How friends will see you"
				/>
			</div>

			<div>
				<label for="email" class="mb-1 block text-sm font-medium text-ink-light">Email</label>
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
				<label for="password" class="mb-1 block text-sm font-medium text-ink-light">Password</label>
				<input
					id="password"
					type="password"
					bind:value={password}
					required
					minlength="8"
					autocomplete="new-password"
					class="w-full rounded-input border border-cream-dark bg-white px-4 py-3 text-base text-ink outline-none transition-colors focus:border-jade"
					placeholder="At least 8 characters"
				/>
				<PasswordStrength {password} />
			</div>

			<div>
				<label for="confirmPassword" class="mb-1 block text-sm font-medium text-ink-light">Confirm Password</label>
				<input
					id="confirmPassword"
					type="password"
					bind:value={confirmPassword}
					required
					autocomplete="new-password"
					class="w-full rounded-input border border-cream-dark bg-white px-4 py-3 text-base text-ink outline-none transition-colors focus:border-jade"
					placeholder="Repeat your password"
				/>
			</div>

			<button
				type="submit"
				disabled={submitting || !email || !password || !confirmPassword}
				class="flex min-h-12 w-full items-center justify-center rounded-button bg-jade text-base font-semibold text-white transition-opacity active:scale-[0.98] disabled:opacity-50"
			>
				{submitting ? 'Creating account...' : 'Create Account'}
			</button>
		</form>

		<p class="mt-8 text-center text-sm text-ink-muted">
			Already have an account?
			<a href="/login" class="font-medium text-jade">Sign in</a>
		</p>
	</div>
</div>
