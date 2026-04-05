<script lang="ts">
	interface Option {
		value: number;
		label: string;
	}

	let {
		label = '',
		placeholder = 'Select...',
		options = [],
		value = $bindable<number | undefined>(undefined),
	}: {
		label?: string;
		placeholder?: string;
		options: Option[];
		value: number | undefined;
	} = $props();

	let open = $state(false);

	let selectedLabel = $derived(
		options.find((o) => o.value === value)?.label || '',
	);

	function select(v: number) {
		value = value === v ? undefined : v;
		open = false;
	}

	function handleBlur(e: FocusEvent) {
		const related = e.relatedTarget as HTMLElement | null;
		if (!related?.closest('.dropdown-container')) {
			open = false;
		}
	}
</script>

<!-- svelte-ignore a11y_no_static_element_interactions -->
<div class="dropdown-container relative" onblur={handleBlur}>
	{#if label}
		<span class="mb-1 block text-sm font-medium text-ink-light">{label}</span>
	{/if}

	<button
		type="button"
		class="flex w-full items-center justify-between rounded-input border border-cream-dark bg-white px-4 py-3 text-left text-base transition-colors {open ? 'border-jade' : ''}"
		onclick={() => (open = !open)}
	>
		<span class={selectedLabel ? 'text-ink' : 'text-ink-muted'}>
			{selectedLabel || placeholder}
		</span>
		<svg
			class="h-4 w-4 text-ink-muted transition-transform {open ? 'rotate-180' : ''}"
			viewBox="0 0 24 24"
			fill="none"
			stroke="currentColor"
			stroke-width="2"
			stroke-linecap="round"
			stroke-linejoin="round"
		>
			<polyline points="6 9 12 15 18 9" />
		</svg>
	</button>

	{#if open}
		<div class="absolute left-0 right-0 top-full z-50 mt-1 max-h-52 overflow-y-auto rounded-card border border-cream-dark bg-white shadow-elevated">
			{#each options as option}
				<button
					type="button"
					class="flex w-full items-center px-4 py-2.5 text-left text-sm transition-colors active:bg-cream {option.value === value ? 'bg-jade/5 font-medium text-jade' : 'text-ink'}"
					onclick={() => select(option.value)}
				>
					{option.label}
					{#if option.value === value}
						<svg class="ml-auto h-4 w-4 text-jade" viewBox="0 0 16 16" fill="currentColor">
							<path d="M13.78 4.22a.75.75 0 0 1 0 1.06l-7.25 7.25a.75.75 0 0 1-1.06 0L2.22 9.28a.75.75 0 0 1 1.06-1.06L6 10.94l6.72-6.72a.75.75 0 0 1 1.06 0Z" />
						</svg>
					{/if}
				</button>
			{/each}
		</div>
	{/if}
</div>
