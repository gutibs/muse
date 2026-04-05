<script lang="ts">
	let { password = '' }: { password: string } = $props();

	interface Check {
		label: string;
		test: (pw: string) => boolean;
	}

	const checks: Check[] = [
		{ label: '8+ characters', test: (pw) => pw.length >= 8 },
		{ label: 'Uppercase letter', test: (pw) => /[A-Z]/.test(pw) },
		{ label: 'Lowercase letter', test: (pw) => /[a-z]/.test(pw) },
		{ label: 'Number', test: (pw) => /\d/.test(pw) },
		{ label: 'Special character', test: (pw) => /[^A-Za-z0-9]/.test(pw) },
	];

	let passed = $derived(checks.filter((c) => c.test(password)).length);
	let strength = $derived(
		password.length === 0 ? 0 : passed <= 2 ? 1 : passed <= 3 ? 2 : passed <= 4 ? 3 : 4
	);

	const labels = ['', 'Weak', 'Fair', 'Good', 'Strong'] as const;
	const colors = ['', 'bg-blush', 'bg-blush-light', 'bg-jade-light', 'bg-jade'] as const;
	const textColors = ['', 'text-blush', 'text-blush-light', 'text-jade-light', 'text-jade'] as const;
</script>

{#if password.length > 0}
	<div class="mt-2 space-y-2">
		<div class="flex gap-1">
			{#each [1, 2, 3, 4] as level}
				<div
					class="h-1 flex-1 rounded-full transition-colors {strength >= level ? colors[strength] : 'bg-cream-dark'}"
				></div>
			{/each}
		</div>
		<div class="flex items-center justify-between">
			<span class="text-xs font-medium {textColors[strength]}">{labels[strength]}</span>
		</div>
		<ul class="space-y-0.5">
			{#each checks as check}
				<li class="flex items-center gap-1.5 text-xs {check.test(password) ? 'text-jade' : 'text-ink-muted'}">
					{#if check.test(password)}
						<svg class="h-3 w-3 shrink-0" viewBox="0 0 16 16" fill="currentColor">
							<path d="M13.78 4.22a.75.75 0 0 1 0 1.06l-7.25 7.25a.75.75 0 0 1-1.06 0L2.22 9.28a.75.75 0 0 1 1.06-1.06L6 10.94l6.72-6.72a.75.75 0 0 1 1.06 0Z" />
						</svg>
					{:else}
						<svg class="h-3 w-3 shrink-0" viewBox="0 0 16 16" fill="currentColor">
							<circle cx="8" cy="8" r="3" />
						</svg>
					{/if}
					{check.label}
				</li>
			{/each}
		</ul>
	</div>
{/if}
