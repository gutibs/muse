<script lang="ts">
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import LevelSelector from '$lib/components/LevelSelector.svelte';
	import LocationPicker from '$lib/components/LocationPicker.svelte';
	import TagChips from '$lib/components/TagChips.svelte';
	import RatingStars from '$lib/components/RatingStars.svelte';
	import SegmentedControl from '$lib/components/SegmentedControl.svelte';
	import StatusToggle from '$lib/components/StatusToggle.svelte';
	import TagCheckboxes from '$lib/components/TagCheckboxes.svelte';
	import { t } from '$lib/i18n/index.svelte';
	import { googleImportErrorKey, importPlace } from '$lib/services/google-import';
	import { pinsService } from '$lib/services/pins.service';
	import { authStore } from '$lib/stores/auth.store.svelte';
	import { placesService, type PlaceSuggestion } from '$lib/services/places.service';
	import { restaurantsService } from '$lib/services/restaurants.service';
	import type { Cuisine, PinStatus, PinVisibility, Restaurant, Tag } from '$lib/types';
	import { AXES } from '$lib/utils/taxonomy';
	import { suggestOccasion } from '$lib/utils/suggest-occasion';
	import { ApiError } from '$lib/types';
	import { extractFirstDrfError } from '$lib/utils/api-error';
	import { logSilent } from '$lib/utils/logger';
	import { VISIBILITY_OPTIONS, visibilityToSubmit } from '$lib/utils/pin-visibility';

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
	let newCuisineIds = $state<number[]>([]);
	let newLat = $state<number | null>(null);
	let newLng = $state<number | null>(null);
	let newPriceLevel = $state(0);
	let newReservationUrl = $state('');
	let newQualityLevel = $state(0);
	let newTagIds = $state<number[]>([]);

	// Pin fields
	let status = $state<PinStatus>('visited');
	let rating = $state(0);
	let comment = $state('');
	let selectedTags = $state<number[]>([]);
	// Arranca en la preferencia del perfil, y mientras no se toque el pin se
	// guarda sin nivel propio: así sigue moviéndose con esa preferencia.
	const profileVisibility = $derived(authStore.user?.defaultPinVisibility ?? 'public');
	let visibility = $state<PinVisibility>('public');
	$effect(() => {
		visibility = profileVisibility;
	});

	// Reference data
	let cuisines = $state<Cuisine[]>([]);
	let tags = $state<Tag[]>([]);
	// Un solo fetch del catálogo, repartido según para qué sirve cada eje.
	let axisTags = $derived(tags.filter((tag) => (AXES as readonly string[]).includes(tag.kind)));
	let dietaryTags = $derived(tags.filter((tag) => tag.kind === 'dietary'));

	// Lo que propuso el sistema, no lo que eligió el usuario. Se guarda
	// aparte para poder marcarlo como sugerencia y para poder retirarlo si
	// deja de corresponder.
	let suggestedSlugs = $state<string[]>([]);
	let suggestionsApplied = $state(false);

	/**
	 * Marca sola lo que ya sabemos, al entrar al paso 2.
	 *
	 * Dos orígenes distintos y con distinto derecho a estar ahí: las
	 * características del local (terraza, música en vivo, perros) son un
	 * hecho que Google afirma y viajan en el restaurante; la ocasión es una
	 * corazonada a partir de la hora, así que sólo se propone al registrar
	 * una visita — guardar un lugar al mediodía no dice nada sobre cuándo
	 * pensás ir.
	 */
	$effect(() => {
		if (step !== 2 || suggestionsApplied || tags.length === 0) return;
		suggestionsApplied = true;

		const propuestos: string[] = [];

		for (const tag of selectedRestaurant?.tagsDetail ?? []) {
			if (tag.kind === 'scene') propuestos.push(tag.slug);
		}

		if (status === 'visited') {
			const ocasion = suggestOccasion();
			if (ocasion) propuestos.push(ocasion);
		}

		const ids = axisTags.filter((tag) => propuestos.includes(tag.slug)).map((tag) => tag.id);
		if (ids.length === 0) return;
		suggestedSlugs = propuestos;
		selectedTags = [...new Set([...selectedTags, ...ids])];
	});

	/**
	 * Pasar a "quiero ir" retira la ocasión sugerida, no la que el usuario
	 * haya elegido a mano.
	 */
	$effect(() => {
		if (status !== 'to_visit' || suggestedSlugs.length === 0) return;
		const ocasiones = axisTags
			.filter((tag) => tag.kind === 'occasion' && suggestedSlugs.includes(tag.slug))
			.map((tag) => tag.id);
		if (ocasiones.length === 0) return;
		selectedTags = selectedTags.filter((id) => !ocasiones.includes(id));
		suggestedSlugs = suggestedSlugs.filter(
			(slug) => !axisTags.some((tag) => tag.slug === slug && tag.kind === 'occasion')
		);
	});

	// Load reference data
	$effect(() => {
		restaurantsService.cuisines().then((c) => (cuisines = c));
		restaurantsService.tags().then((all) => (tags = all));
	});

	// If we got here from `/restaurant/<id>` → "Add to my pins", the restaurant
	// id is in the query string. Pre-fetch it and jump straight to step 2 so
	// the user doesn't have to re-search/re-type the name they already picked.
	$effect(() => {
		const idParam = page.url.searchParams.get('restaurantId');
		const id = idParam ? Number(idParam) : NaN;
		if (!Number.isFinite(id) || id <= 0) return;
		// Avoid clobbering state if user already navigated forward.
		if (selectedRestaurant || creatingNew || step !== 1) return;
		restaurantsService.get(id).then(
			(r) => {
				if (!selectedRestaurant && !creatingNew && step === 1) {
					selectedRestaurant = r;
					step = 2;
				}
			},
			() => {
				// Silent: user can still search manually.
			}
		);
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
			} catch (err) {
				searchResults = [];
				googleResults = [];
				logSilent('pin:new:search', err);
			}
			searching = false;
		}, 300);
	}

	async function selectFromGoogle(suggestion: PlaceSuggestion) {
		importingPlaceId = suggestion.placeId;
		error = '';
		try {
			selectedRestaurant = await importPlace(suggestion.placeId);
			creatingNew = false;
			step = 2;
		} catch (err) {
			// Now handles 429 too, which this screen silently reported as a
			// generic "couldn't import" while the search screen named it.
			const key = googleImportErrorKey(err);
			error = key ? t(key) : t('pin.cantImport');
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
					cuisines: newCuisineIds.length > 0 ? newCuisineIds : undefined,
					tagIds: newTagIds.length > 0 ? newTagIds : undefined,
					priceLevel: newPriceLevel || undefined,
					reservationUrl: newReservationUrl.trim() || undefined,
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
				tagIds: selectedTags.length > 0 ? selectedTags : undefined,
				visibility: visibilityToSubmit(visibility, null, profileVisibility),
			});

			goto('/map');
		} catch (err) {
			if (err instanceof ApiError && err.status === 409) {
				error = t('pin.alreadyPinned');
			} else {
				error = extractFirstDrfError(err);
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
			aria-label={t('common.back')}
		>
			<svg class="h-6 w-6 text-ink" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
				<polyline points="15 18 9 12 15 6" />
			</svg>
		</button>
		<h1 class="text-lg font-semibold text-ink">
			{step === 1 && !creatingNew ? t('pin.addPin') : step === 1 && creatingNew ? t('pin.newRestaurant') : t('pin.pinDetails')}
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
					<label for="search" class="mb-1 block text-sm font-medium text-ink-light">{t('pin.searchRestaurant')}</label>
					<input
						id="search"
						type="text"
						bind:value={searchQuery}
						oninput={handleSearch}
						class="w-full rounded-input border border-cream-dark bg-white px-4 py-3 text-base text-ink outline-none focus:border-jade"
						placeholder={t('search.placeholder')}
					/>
				</div>

				{#if searching}
					<p class="text-center text-sm text-ink-muted">{t('pin.searching')}</p>
				{/if}

				{#if searchResults.length > 0}
					<div>
						<p class="mb-2 text-xs font-semibold uppercase tracking-wide text-ink-muted">{t('pin.alreadyOnMuse')}</p>
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
						<p class="mb-2 text-xs font-semibold uppercase tracking-wide text-ink-muted">{t('pin.fromGoogle')}</p>
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
					<p class="py-4 text-center text-sm text-ink-muted">{t('pin.noResults')}</p>
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
						<div class="text-sm font-semibold text-jade">{t('pin.addManually')}</div>
						<div class="text-xs text-ink-muted">{t('pin.cantFindIt')}</div>
					</div>
				</button>
			</div>

		<!-- Step 1b: New restaurant form -->
		{:else if step === 1 && creatingNew}
			<div class="space-y-5">
				<div>
					<label for="name" class="mb-1 block text-sm font-medium text-ink-light">{t('pin.name')}</label>
					<input
						id="name"
						type="text"
						bind:value={newName}
						required
						class="w-full rounded-input border border-cream-dark bg-white px-4 py-3 text-base text-ink outline-none focus:border-jade"
						placeholder={t('pin.restaurantNamePlaceholder')}
					/>
				</div>

				<!-- Location Picker (mini map) -->
				<LocationPicker bind:lat={newLat} bind:lng={newLng} bind:address={newAddress} bind:city={newCity} bind:country={newCountry} />

				<!-- Address (editable, pre-filled by geocoding) -->
				<div>
					<label for="address" class="mb-1 block text-sm font-medium text-ink-light">{t('pin.address')}</label>
					<input
						id="address"
						type="text"
						bind:value={newAddress}
						class="w-full rounded-input border border-cream-dark bg-white px-4 py-3 text-base text-ink outline-none focus:border-jade"
						placeholder={t('pin.address')}
					/>
				</div>

				<div>
					<label for="city" class="mb-1 block text-sm font-medium text-ink-light">{t('pin.city')}</label>
					<input
						id="city"
						type="text"
						bind:value={newCity}
						class="w-full rounded-input border border-cream-dark bg-white px-4 py-3 text-base text-ink outline-none focus:border-jade"
						placeholder={t('pin.city')}
					/>
				</div>

				<div>
					<label for="reservation-url" class="mb-1 block text-sm font-medium text-ink-light">
						{t('restaurant.reservationUrl')}
					</label>
					<input
						id="reservation-url"
						type="url"
						inputmode="url"
						bind:value={newReservationUrl}
						class="w-full rounded-input border border-cream-dark bg-white px-4 py-3 text-base text-ink outline-none focus:border-jade"
						placeholder="https://"
					/>
					<p class="mt-1 text-xs text-ink-muted">{t('restaurant.reservationUrlHelp')}</p>
				</div>

				<!-- Cuisines (multi-select) -->
				{#if cuisines.length > 0}
					<div>
						<span class="mb-2 block text-sm font-medium text-ink-light">{t('pin.cuisine')}</span>
						<TagCheckboxes tags={cuisines} bind:selected={newCuisineIds} />
					</div>
				{/if}

				<!-- Quality (forks) -->
				<LevelSelector label={t('pin.quality')} variant="quality" bind:value={newQualityLevel} />

				<!-- Price ($) -->
				<LevelSelector label={t('pin.price')} variant="price" bind:value={newPriceLevel} />

				<!-- Atributos del local. El vibe NO va acá: es la opinión de quien
				     guarda el lugar, y se pregunta en el paso 2 junto con la
				     ocasión. Antes esta lista traía la tabla entera de tags y
				     ofrecía "vegetarian" como si fuera un ambiente. -->
				{#if dietaryTags.length > 0}
					<div>
						<span class="mb-2 block text-sm font-medium text-ink-light">{t('pin.dietaryOptions')}</span>
						<TagCheckboxes tags={dietaryTags} bind:selected={newTagIds} />
					</div>
				{/if}

				<button
					onclick={confirmNewRestaurant}
					disabled={!newName || !newLat || !newLng}
					class="flex min-h-12 w-full items-center justify-center rounded-button bg-jade text-base font-semibold text-white active:scale-[0.98] disabled:opacity-50"
				>
					{t('pin.continue')}
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
					<span class="mb-2 block text-sm font-medium text-ink-light">{t('pin.status')}</span>
					<StatusToggle bind:value={status} />
				</div>

				<!-- Quién lo ve -->
				<div>
					<span class="mb-2 block text-sm font-medium text-ink-light">{t('pin.visibility')}</span>
					<SegmentedControl bind:value={visibility} options={VISIBILITY_OPTIONS()} />
					<p class="mt-1.5 text-xs text-ink-muted">{t('pin.visibilityHelp')}</p>
				</div>

				<!-- Rating (only if visited) -->
				{#if status === 'visited'}
					<div>
						<span class="mb-2 block text-sm font-medium text-ink-light">{t('pin.rating')}</span>
						<RatingStars bind:value={rating} />
					</div>
				{/if}

				<!-- My Notes -->
				<div>
					<label for="comment" class="mb-1 block text-sm font-medium text-ink-light">{t('pin.myNotes')}</label>
					<textarea
						id="comment"
						bind:value={comment}
						rows="3"
						class="w-full rounded-input border border-cream-dark bg-white px-4 py-3 text-base text-ink outline-none focus:border-jade"
						placeholder={status === 'visited' ? t('pin.shareExperience') : t('pin.whyVisit')}
					></textarea>
				</div>

				<!-- Los tres ejes del pin: vibe, ocasión y características -->
				{#if axisTags.length > 0}
					<TagChips
						tags={axisTags}
						grouped
						suggested={suggestedSlugs}
						bind:selected={selectedTags}
					/>
				{/if}

				<!-- Submit -->
				<button
					onclick={handleSubmit}
					disabled={submitting || (status === 'visited' && rating === 0)}
					class="flex min-h-12 w-full items-center justify-center rounded-button bg-jade text-base font-semibold text-white active:scale-[0.98] disabled:opacity-50"
				>
					{submitting ? t('pin.saving') : t('pin.savePin')}
				</button>
			</div>
		{/if}
	</div>
</div>
