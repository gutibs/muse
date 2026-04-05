<script lang="ts">
	import { goto } from '$app/navigation';
	import { authStore } from '$lib/stores/auth.store.svelte';
	import { ApiError } from '$lib/types';

	let email = $state('');
	let password = $state('');
	let error = $state('');
	let submitting = $state(false);

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
					? 'Invalid email or password'
					: 'Something went wrong. Please try again.';
			} else {
				error = 'Connection error. Please check your network.';
			}
		} finally {
			submitting = false;
		}
	}
</script>

<div class="flex h-full flex-col items-center justify-center bg-cream px-6">
	<div class="w-full max-w-sm">
		<h1 class="mb-2 text-center font-serif text-4xl font-bold text-jade-dark">Muse</h1>
		<p class="mb-10 text-center text-sm text-ink-muted">Where friends eat well</p>

		<form onsubmit={handleSubmit} class="space-y-4">
			{#if error}
				<div class="rounded-button bg-blush-light/20 px-4 py-3 text-sm text-blush">
					{error}
				</div>
			{/if}

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
					autocomplete="current-password"
					class="w-full rounded-input border border-cream-dark bg-white px-4 py-3 text-base text-ink outline-none transition-colors focus:border-jade"
					placeholder="Enter your password"
				/>
			</div>

			<button
				type="submit"
				disabled={submitting || !email || !password}
				class="flex min-h-12 w-full items-center justify-center rounded-button bg-jade text-base font-semibold text-white transition-opacity active:scale-[0.98] disabled:opacity-50"
			>
				{submitting ? 'Signing in...' : 'Sign In'}
			</button>
		</form>

		<p class="mt-8 text-center text-sm text-ink-muted">
			Don't have an account?
			<a href="/register" class="font-medium text-jade">Create one</a>
		</p>
	</div>
</div>
