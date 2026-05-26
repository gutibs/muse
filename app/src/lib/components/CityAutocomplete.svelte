<script lang="ts">
	import { placesService, type CitySuggestion } from '$lib/services/places.service';

	let {
		value = $bindable(''),
		placeholder = 'City',
		id = 'city-autocomplete',
		biasLat,
		biasLng,
		onPick,
		onSubmit,
	}: {
		value?: string;
		placeholder?: string;
		id?: string;
		biasLat?: number;
		biasLng?: number;
		onPick?: (suggestion: CitySuggestion) => void;
		onSubmit?: () => void;
	} = $props();

	let suggestions = $state<CitySuggestion[]>([]);
	let showDropdown = $state(false);
	let loading = $state(false);
	let debounceTimer: ReturnType<typeof setTimeout> | null = null;
	let container: HTMLDivElement;

	$effect(() => {
		// Close on outside pointerdown instead of input blur. The blur-based
		// close caused a race on /map: the Android virtual keyboard triggers a
		// transient blur on the absolutely-positioned input, closing the
		// dropdown 150ms later — before the autocomplete request returns. With
		// outside-pointerdown the dropdown stays open until the user actually
		// taps somewhere else (a suggestion item still closes via `pick`).
		function onDocPointerDown(e: PointerEvent) {
			if (!showDropdown) return;
			if (container && !container.contains(e.target as Node)) {
				showDropdown = false;
			}
		}
		document.addEventListener('pointerdown', onDocPointerDown);
		return () => {
			document.removeEventListener('pointerdown', onDocPointerDown);
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
				const res = await placesService.cityAutocomplete(value.trim(), biasLat, biasLng);
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
		onkeydown={(e) => {
			if (e.key === 'Enter') {
				showDropdown = false;
				onSubmit?.();
			}
		}}
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
