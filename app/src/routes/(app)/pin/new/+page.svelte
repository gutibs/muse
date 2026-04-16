<script lang="ts">
	import { goto } from '$app/navigation';
	import Dropdown from '$lib/components/Dropdown.svelte';
	import LevelSelector from '$lib/components/LevelSelector.svelte';
	import LocationPicker from '$lib/components/LocationPicker.svelte';
	import PersonaChips from '$lib/components/PersonaChips.svelte';
	import RatingStars from '$lib/components/RatingStars.svelte';
	import StatusToggle from '$lib/components/StatusToggle.svelte';
	import TagCheckboxes from '$lib/components/TagCheckboxes.svelte';
	import { pinsService } from '$lib/services/pins.service';
	import { placesService, type PlaceSuggestion } from '$lib/services/places.service';
	import { restaurantsService } from '$lib/services/restaurants.service';
	import type { Cuisine, Persona, PinStatus, Restaurant, Tag } from '$lib/types';
	import { ApiError } from '$lib/types';

	// State
	let step = $state(1);
	let submitting = $state(false);
	let error = $state('');

	// Restaurant search
	let searchQuery = $state('');
	let searchResults = $state<Restaurant[]>([]);
	let googleResults = $state<PlaceSuggestion[]>([]);
	let searching = $state(false);
	let importingPlaceId = $state<string | null>(null);
	let selectedRestaurant = $state<Restaurant | null>(null);
	let creatingNew = $state(false);

	// New restaurant fields
	let newName = $state('');
	let newAddress = $state('');
	let newCity = $state('');
	let newCountry = $state('');
	let newCuisine = $state<number | undefined>(undefined);
	let newLat = $state<number | null>(null);
	let newLng = $state<number | null>(null);
	let newPriceLevel = $state(0);
	let newQualityLevel = $state(0);
	let newTagIds = $state<number[]>([]);

	// Pin fields
	let status = $state<PinStatus>('visited');
	let rating = $state(0);
	let comment = $state('');
	let selectedPersonas = $state<number[]>([]);

	// Reference data
	let cuisines = $state<Cuisine[]>([]);
	let personas = $state<Persona[]>([]);
	let tags = $state<Tag[]>([]);

	let cuisineOptions = $derived(cuisines.map((c) => ({ value: c.id, label: c.name })));

	// Load reference data
	$effect(() => {
		restaurantsService.cuisines().then((c) => (cuisines = c));
		restaurantsService.tags().then((t) => (tags = t));
		pinsService.personas().then((p) => (personas = p));
	});

	// Debounced search — queries both our DB and Google Places in parallel
	let searchTimeout: ReturnType<typeof setTimeout>;
	function handleSearch() {
		clearTimeout(searchTimeout);
		if (searchQuery.length < 2) {
			searchResults = [];
			googleResults = [];
			return;
		}
		searchTimeout = setTimeout(async () => {
			searching = true;
			const query = searchQuery;
			try {
				const [dbRes, placesRes] = await Promise.allSettled([
					restaurantsService.list({ search: query }),
					placesService.autocomplete(query),
				]);
				searchResults = dbRes.status === 'fulfilled' ? dbRes.value.results : [];
				googleResults = placesRes.status === 'fulfilled' ? placesRes.value.results : [];
			} catch {
				searchResults = [];
				googleResults = [];
			}
			searching = false;
		}, 300);
	}

	async function selectFromGoogle(suggestion: PlaceSuggestion) {
		importingPlaceId = suggestion.placeId;
		error = '';
		try {
			const details = await placesService.details(suggestion.placeId);
			const restaurant = await restaurantsService.fromGoogle({
				placeId: details.placeId,
				name: details.name,
				address: details.address,
				city: details.city,
				country: details.country,
				lat: details.lat,
				lng: details.lng,
				website: details.website,
				phone: details.phone,
				imageUrl: details.imageUrl,
				openingHours: details.openingHours,
			});
			selectedRestaurant = restaurant;
			creatingNew = false;
			step = 2;
		} catch {
			error = 'Could not import this place. Try another.';
		} finally {
			importingPlaceId = null;
		}
	}

	function selectRestaurant(r: Restaurant) {
		selectedRestaurant = r;
		creatingNew = false;
		step = 2;
	}

	function startNewRestaurant() {
		creatingNew = true;
		selectedRestaurant = null;
		newName = searchQuery;
	}

	function confirmNewRestaurant() {
		if (!newName || !newLat || !newLng) return;
		step = 2;
	}

	function goBack() {
		if (step === 2) {
			step = 1;
		} else if (creatingNew) {
			creatingNew = false;
		} else {
			history.back();
		}
	}

	async function handleSubmit() {
		error = '';
		submitting = true;

		try {
			let restaurantId: number;

			if (creatingNew) {
				const restaurant = await restaurantsService.create({
					name: newName,
					latitude: newLat!,
					longitude: newLng!,
					address: newAddress,
					city: newCity,
					country: newCountry,
					cuisine: newCuisine,
					tagIds: newTagIds.length > 0 ? newTagIds : undefined,
					priceLevel: newPriceLevel || undefined,
					qualityLevel: newQualityLevel || undefined,
				});
				restaurantId = restaurant.id;
				// New restaurant needs approval — can't pin it yet
				if (restaurant.approvalStatus === 'pending') {
					goto(`/home?pending=${encodeURIComponent(restaurant.name)}`);
					return;
				}
			} else {
				restaurantId = selectedRestaurant!.id;
			}

			await pinsService.create({
				restaurant: restaurantId,
				status,
				rating: status === 'visited' ? rating : undefined,
				comment: comment || undefined,
				personaIds: selectedPersonas.length > 0 ? selectedPersonas : undefined,
			});

			goto('/map');
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

<div class="flex h-full flex-col bg-cream">
	<!-- Header -->
	<header class="flex shrink-0 items-center gap-3 px-4 py-3">
		<button
			onclick={goBack}
			class="flex min-h-11 min-w-11 items-center justify-center rounded-lg active:scale-95"
			aria-label="Go back"
		>
			<svg class="h-6 w-6 text-ink" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
				<polyline points="15 18 9 12 15 6" />
			</svg>
		</button>
		<h1 class="text-lg font-semibold text-ink">
			{step === 1 && !creatingNew ? 'Add Pin' : step === 1 && creatingNew ? 'New Restaurant' : 'Pin Details'}
		</h1>
	</header>

	<!-- Content -->
	<div class="flex-1 overflow-y-auto px-5 pb-6">
		{#if error}
			<div class="mb-4 rounded-button bg-blush-light/20 px-4 py-3 text-sm text-blush">
				{error}
			</div>
		{/if}

		<!-- Step 1a: Search existing restaurant -->
		{#if step === 1 && !creatingNew}
			<div class="space-y-4">
				<div>
					<label for="search" class="mb-1 block text-sm font-medium text-ink-light">Search restaurant</label>
					<input
						id="search"
						type="text"
						bind:value={searchQuery}
						oninput={handleSearch}
						class="w-full rounded-input border border-cream-dark bg-white px-4 py-3 text-base text-ink outline-none focus:border-jade"
						placeholder="Restaurant name..."
					/>
				</div>

				{#if searching}
					<p class="text-center text-sm text-ink-muted">Searching...</p>
				{/if}

				{#if searchResults.length > 0}
					<div>
						<p class="mb-2 text-xs font-semibold uppercase tracking-wide text-ink-muted">Already on Muse</p>
						<div class="space-y-2">
							{#each searchResults as restaurant}
								<button
									onclick={() => selectRestaurant(restaurant)}
									class="flex w-full items-center gap-3 rounded-card bg-white p-4 text-left shadow-card active:scale-[0.98]"
								>
									<div class="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-jade/10 text-jade">
										<svg class="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
											<path d="M12 13a3 3 0 1 0 0-6 3 3 0 0 0 0 6Z" />
											<path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7Z" />
										</svg>
									</div>
									<div class="min-w-0 flex-1">
										<div class="truncate text-sm font-semibold text-ink">{restaurant.name}</div>
										<div class="truncate text-xs text-ink-muted">
											{restaurant.city || restaurant.address || 'No location info'}
										</div>
									</div>
									{#if restaurant.averageRating}
										<span class="shrink-0 text-sm font-medium text-rose-400">&#9829; {restaurant.averageRating.toFixed(1)}</span>
									{/if}
								</button>
							{/each}
						</div>
					</div>
				{/if}

				{#if googleResults.length > 0}
					<div>
						<p class="mb-2 text-xs font-semibold uppercase tracking-wide text-ink-muted">From Google</p>
						<div class="space-y-2">
							{#each googleResults as place (place.placeId)}
								<button
									onclick={() => selectFromGoogle(place)}
									disabled={importingPlaceId !== null}
									class="flex w-full items-center gap-3 rounded-card bg-white p-4 text-left shadow-card active:scale-[0.98] disabled:opacity-50"
								>
									<div class="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-amber-50 text-amber-700">
										{#if importingPlaceId === place.placeId}
											<div class="h-4 w-4 animate-spin rounded-full border-2 border-amber-700 border-t-transparent"></div>
										{:else}
											<svg class="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
												<path d="M12 13a3 3 0 1 0 0-6 3 3 0 0 0 0 6Z" />
												<path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7Z" />
											</svg>
										{/if}
									</div>
									<div class="min-w-0 flex-1">
										<div class="truncate text-sm font-semibold text-ink">{place.name}</div>
										<div class="truncate text-xs text-ink-muted">{place.address}</div>
									</div>
								</button>
							{/each}
						</div>
					</div>
				{/if}

				{#if searchQuery.length >= 2 && !searching && searchResults.length === 0 && googleResults.length === 0}
					<p class="py-4 text-center text-sm text-ink-muted">No results found</p>
				{/if}

				<button
					onclick={startNewRestaurant}
					class="flex w-full items-center gap-3 rounded-card border-2 border-dashed border-jade/30 p-4 text-left active:scale-[0.98]"
				>
					<div class="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-jade text-white">
						<svg class="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
							<line x1="12" y1="5" x2="12" y2="19" />
							<line x1="5" y1="12" x2="19" y2="12" />
						</svg>
					</div>
					<div>
						<div class="text-sm font-semibold text-jade">Add manually</div>
						<div class="text-xs text-ink-muted">If you can't find it above</div>
					</div>
				</button>
			</div>

		<!-- Step 1b: New restaurant form -->
		{:else if step === 1 && creatingNew}
			<div class="space-y-5">
				<div>
					<label for="name" class="mb-1 block text-sm font-medium text-ink-light">Name</label>
					<input
						id="name"
						type="text"
						bind:value={newName}
						required
						class="w-full rounded-input border border-cream-dark bg-white px-4 py-3 text-base text-ink outline-none focus:border-jade"
						placeholder="Restaurant name"
					/>
				</div>

				<!-- Location Picker (mini map) -->
				<LocationPicker bind:lat={newLat} bind:lng={newLng} bind:address={newAddress} bind:city={newCity} bind:country={newCountry} />

				<!-- Address (editable, pre-filled by geocoding) -->
				<div>
					<label for="address" class="mb-1 block text-sm font-medium text-ink-light">Address</label>
					<input
						id="address"
						type="text"
						bind:value={newAddress}
						class="w-full rounded-input border border-cream-dark bg-white px-4 py-3 text-base text-ink outline-none focus:border-jade"
						placeholder="Street address"
					/>
				</div>

				<div>
					<label for="city" class="mb-1 block text-sm font-medium text-ink-light">City</label>
					<input
						id="city"
						type="text"
						bind:value={newCity}
						class="w-full rounded-input border border-cream-dark bg-white px-4 py-3 text-base text-ink outline-none focus:border-jade"
						placeholder="City"
					/>
				</div>

				<!-- Cuisine dropdown (styled) -->
				<Dropdown
					label="Cuisine"
					placeholder="Select cuisine (optional)"
					options={cuisineOptions}
					bind:value={newCuisine}
				/>

				<!-- Quality (forks) -->
				<LevelSelector label="Quality" variant="quality" bind:value={newQualityLevel} />

				<!-- Price ($) -->
				<LevelSelector label="Price" variant="price" bind:value={newPriceLevel} />

				<!-- Tags -->
				{#if tags.length > 0}
					<div>
						<span class="mb-2 block text-sm font-medium text-ink-light">Vibe</span>
						<TagCheckboxes {tags} bind:selected={newTagIds} />
					</div>
				{/if}

				<button
					onclick={confirmNewRestaurant}
					disabled={!newName || !newLat || !newLng}
					class="flex min-h-12 w-full items-center justify-center rounded-button bg-jade text-base font-semibold text-white active:scale-[0.98] disabled:opacity-50"
				>
					Continue
				</button>
			</div>

		<!-- Step 2: Pin details -->
		{:else if step === 2}
			<div class="space-y-6">
				<!-- Selected restaurant info -->
				<div class="rounded-card bg-white p-4 shadow-card">
					<h3 class="font-serif text-lg font-semibold text-ink">
						{creatingNew ? newName : selectedRestaurant?.name}
					</h3>
					{#if !creatingNew && selectedRestaurant?.city}
						<p class="text-sm text-ink-muted">{selectedRestaurant.city}</p>
					{:else if creatingNew && newCity}
						<p class="text-sm text-ink-muted">{newCity}</p>
					{/if}
				</div>

				<!-- Status -->
				<div>
					<span class="mb-2 block text-sm font-medium text-ink-light">Status</span>
					<StatusToggle bind:value={status} />
				</div>

				<!-- Rating (only if visited) -->
				{#if status === 'visited'}
					<div>
						<span class="mb-2 block text-sm font-medium text-ink-light">Rating</span>
						<RatingStars bind:value={rating} />
					</div>
				{/if}

				<!-- My Notes -->
				<div>
					<label for="comment" class="mb-1 block text-sm font-medium text-ink-light">My Notes</label>
					<textarea
						id="comment"
						bind:value={comment}
						rows="3"
						class="w-full rounded-input border border-cream-dark bg-white px-4 py-3 text-base text-ink outline-none focus:border-jade"
						placeholder="Share your experience..."
					></textarea>
				</div>

				<!-- Personas -->
				{#if personas.length > 0}
					<div>
						<span class="mb-2 block text-sm font-medium text-ink-light">Occasion</span>
						<PersonaChips {personas} bind:selected={selectedPersonas} />
					</div>
				{/if}

				<!-- Submit -->
				<button
					onclick={handleSubmit}
					disabled={submitting || (status === 'visited' && rating === 0)}
					class="flex min-h-12 w-full items-center justify-center rounded-button bg-jade text-base font-semibold text-white active:scale-[0.98] disabled:opacity-50"
				>
					{submitting ? 'Saving...' : 'Save Pin'}
				</button>
			</div>
		{/if}
	</div>
</div>
