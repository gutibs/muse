<script lang="ts">
	import { placesService, type CitySuggestion } from '$lib/services/places.service';

	let {
		value = $bindable(''),
		placeholder = 'City',
		id = 'city-autocomplete',
		onPick,
	}: {
		value?: string;
		placeholder?: string;
		id?: string;
		onPick?: (suggestion: CitySuggestion) => void;
	} = $props();

	let suggestions = $state<CitySuggestion[]>([]);
	let showDropdown = $state(false);
	let loading = $state(false);
	let debounceTimer: ReturnType<typeof setTimeout> | null = null;
	let container: HTMLDivElement;

	$effect(() => {
		return () => {
			if (debounceTimer) clearTimeout(debounceTimer);
		};
	});

	function onInput() {
		showDropdown = true;
		if (debounceTimer) clearTimeout(debounceTimer);
		if (!value || value.trim().length < 2) {
			suggestions = [];
			return;
		}
		debounceTimer = setTimeout(async () => {
			loading = true;
			try {
				const res = await placesService.cityAutocomplete(value.trim());
				suggestions = res.results;
			} catch {
				suggestions = [];
			} finally {
				loading = false;
			}
		}, 250);
	}

	function pick(s: CitySuggestion) {
		value = s.name;
		suggestions = [];
		showDropdown = false;
		onPick?.(s);
	}

	function onBlur() {
		// Delay hiding so click on suggestion registers
		setTimeout(() => (showDropdown = false), 150);
	}

	function onFocus() {
		if (suggestions.length > 0) showDropdown = true;
	}
</script>

<div class="relative" bind:this={container}>
	<input
		{id}
		type="text"
		bind:value
		oninput={onInput}
		onfocus={onFocus}
		onblur={onBlur}
		autocomplete="off"
		{placeholder}
		class="w-full rounded-input border border-cream-dark bg-white px-4 py-3 text-base text-ink outline-none focus:border-jade"
	/>

	{#if showDropdown && (suggestions.length > 0 || loading)}
		<div class="absolute left-0 right-0 top-full z-50 mt-1 max-h-64 overflow-y-auto rounded-card bg-white shadow-elevated">
			{#if loading && suggestions.length === 0}
				<div class="flex items-center justify-center p-3">
					<div class="h-4 w-4 animate-spin rounded-full border-2 border-jade border-t-transparent"></div>
				</div>
			{:else}
				{#each suggestions as s (s.placeId)}
					<button
						type="button"
						onmousedown={() => pick(s)}
						class="flex w-full items-center gap-2 px-4 py-3 text-left text-sm text-ink hover:bg-cream/50 active:bg-cream"
					>
						<svg class="h-4 w-4 shrink-0 text-ink-muted" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
							<path d="M12 13a3 3 0 1 0 0-6 3 3 0 0 0 0 6Z"/>
							<path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7Z"/>
						</svg>
						<span class="truncate">{s.display}</span>
					</button>
				{/each}
			{/if}
		</div>
	{/if}
</div>
