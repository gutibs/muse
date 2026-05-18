<script lang="ts">
	import Avatar from '$lib/components/Avatar.svelte';
	import CityAutocomplete from '$lib/components/CityAutocomplete.svelte';
	import { authService } from '$lib/services/auth.service';
	import { pinsService } from '$lib/services/pins.service';
	import { restaurantsService } from '$lib/services/restaurants.service';
	import { i18n, t } from '$lib/i18n/index.svelte';
	import { authStore } from '$lib/stores/auth.store.svelte';
	import type { Cuisine, DietaryPreference, Pin, SharedList } from '$lib/types';
	import { extractFirstDrfError } from '$lib/utils/api-error';
	import { copyToClipboard } from '$lib/utils/clipboard';
	import { logSilent } from '$lib/utils/logger';

	const LOCALE_TO_BCP47: Record<string, string> = { en: 'en-GB', es: 'es-AR', it: 'it-IT' };

	let editing = $state(false);

	// My restaurants — server-side filtered (was: read first page then filter
	// locally, which lied about counts for users with 21+ pins).
	let myPins = $state<Pin[]>([]);
	let totalFilteredPins = $state(0);
	let loadingPins = $state(true);
	let pinsFilter = $state<'all' | 'visited' | 'to_visit'>('all');

	let saving = $state(false);
	let error = $state('');
	let success = $state('');

	// Share
	let sharing = $state(false);
	let sharedLists = $state<SharedList[]>([]);

	// Cuisines for dropdown
	let cuisines = $state<Cuisine[]>([]);

	// Dietary preferences fetched from backend (closed set seeded by migration).
	let dietaryOptions = $state<DietaryPreference[]>([]);

	// Edit fields
	let editName = $state('');
	let editBio = $state('');
	let editCity = $state('');
	let editWebsite = $state('');
	let editInstagram = $state('');
	let editPhone = $state('');
	let editDietaryIds = $state<number[]>([]);
	let editCuisine = $state<number | ''>('');

	function toggleDietary(id: number) {
		editDietaryIds = editDietaryIds.includes(id)
			? editDietaryIds.filter((x) => x !== id)
			: [...editDietaryIds, id];
	}

	async function loadSharedLists() {
		try {
			sharedLists = await pinsService.sharedLists();
		} catch (err) {
			logSilent('profile.loadSharedLists', err);
			sharedLists = [];
		}
	}

	async function loadCuisines() {
		try {
			cuisines = await restaurantsService.cuisines();
		} catch (err) {
			logSilent('profile.loadCuisines', err);
			cuisines = [];
		}
	}

	async function loadDietaryOptions() {
		try {
			dietaryOptions = await authService.dietaryPreferences();
		} catch (err) {
			logSilent('profile.loadDietaryOptions', err);
			dietaryOptions = [];
		}
	}

	async function createShareLink() {
		sharing = true;
		try {
			const title = t('profile.someoneList').replace('{name}', authStore.user?.displayName || '');
			const list = await pinsService.createSharedList({ title });
			sharedLists = [...sharedLists, list];
			const fullUrl = list.url.startsWith('http') ? list.url : `${window.location.origin}${list.url}`;
			const ok = await copyToClipboard(fullUrl);
			success = ok ? t('profile.linkCopiedClipboard') : t('profile.linkCopiedClipboard');
			setTimeout(() => (success = ''), 3000);
		} catch (err) {
			logSilent('profile.createShareLink', err);
			error = t('profile.cantCreateLink');
		} finally {
			sharing = false;
		}
	}

	async function deleteSharedList(id: number) {
		try {
			await pinsService.deleteSharedList(id);
			sharedLists = sharedLists.filter((l) => l.id !== id);
		} catch (err) {
			logSilent('profile.deleteSharedList', err);
			error = t('profile.cantRemoveLink');
		}
	}

	async function copyLink(url: string) {
		const fullUrl = url.startsWith('http') ? url : `${window.location.origin}${url}`;
		await copyToClipboard(fullUrl);
		success = t('profile.linkCopied');
		setTimeout(() => (success = ''), 3000);
	}

	async function loadMyPins(filter: 'all' | 'visited' | 'to_visit' = pinsFilter) {
		loadingPins = true;
		try {
			// Server-side filter: backend returns the full filtered count even
			// when only the first page of results is shown.
			const res = await pinsService.list(filter === 'all' ? undefined : { status: filter });
			myPins = res.results;
			totalFilteredPins = res.count;
		} catch (err) {
			logSilent('profile.loadMyPins', err);
			myPins = [];
			totalFilteredPins = 0;
		} finally {
			loadingPins = false;
		}
	}

	function setPinsFilter(next: 'all' | 'visited' | 'to_visit') {
		if (pinsFilter === next) return;
		pinsFilter = next;
		loadMyPins(next);
	}

	$effect(() => {
		if (authStore.isAuthenticated) {
			loadSharedLists();
			loadCuisines();
			loadDietaryOptions();
			loadMyPins(pinsFilter);
			// Refresh user so stats cards reflect any pin add/edit/delete that
			// happened in another route since login. Replaces the local-derived
			// liveStats hack which depended on having the full pin list.
			authStore.refreshUser().catch((err) => logSilent('profile.refreshUser', err));
		}
	});

	function startEditing() {
		editName = authStore.user?.displayName || '';
		editBio = authStore.user?.bio || '';
		editCity = authStore.user?.city || '';
		editWebsite = authStore.user?.website || '';
		editInstagram = authStore.user?.instagram || '';
		editPhone = authStore.user?.phone || '';
		editDietaryIds = (authStore.user?.dietaryPreferencesDetail ?? []).map((p) => p.id);
		editCuisine = authStore.user?.favouriteCuisine || '';
		error = '';
		success = '';
		editing = true;
	}

	function cancelEditing() {
		editing = false;
		error = '';
	}

	async function saveProfile() {
		error = '';
		saving = true;
		try {
			await authStore.updateProfile({
				displayName: editName,
				bio: editBio,
				city: editCity,
				website: editWebsite,
				instagram: editInstagram,
				phone: editPhone,
				dietaryPreferences: editDietaryIds,
				favouriteCuisine: editCuisine || null,
			});
			editing = false;
			success = t('profile.profileUpdated');
			setTimeout(() => (success = ''), 3000);
		} catch (err) {
			error = extractFirstDrfError(err, t('profile.cantUpdate'));
		} finally {
			saving = false;
		}
	}

	let memberSince = $derived(
		authStore.user?.createdAt
			? new Date(authStore.user.createdAt).toLocaleDateString(LOCALE_TO_BCP47[i18n.locale] || 'en-GB', { month: 'long', year: 'numeric' })
			: ''
	);
</script>

<div class="flex h-full flex-col">
	<header class="flex shrink-0 items-center justify-between px-5 py-3">
		<h1 class="text-lg font-semibold text-ink">{t('profile.title')}</h1>
		{#if !editing}
			<button
				onclick={startEditing}
				class="flex min-h-11 items-center gap-1 px-3 text-sm font-medium text-jade active:opacity-70"
			>
				<svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
					<path d="M17 3a2.85 2.83 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5Z" />
					<path d="m15 5 4 4" />
				</svg>
				{t('profile.edit')}
			</button>
		{/if}
	</header>

	<div class="flex-1 overflow-y-auto px-5 pb-6">
		{#if success}
			<div class="mb-4 rounded-card bg-jade/10 px-4 py-3 text-sm font-medium text-jade">
				{success}
			</div>
		{/if}

		<!-- ═══ VIEW MODE ═══ -->
		{#if !editing}
			<!-- Hero card -->
			<div class="rounded-card bg-white p-5 shadow-card">
				<div class="flex flex-col items-center">
					<Avatar
						name={authStore.user?.displayName || ''}
						src={authStore.user?.avatar}
						size={88}
					/>
					<h2 class="mt-3 font-serif text-2xl font-semibold text-ink">
						{authStore.user?.displayName || t('common.yourName')}
					</h2>
					<p class="text-sm text-ink-muted">{authStore.user?.email}</p>

					<!-- Badges row -->
					<div class="mt-3 flex flex-wrap justify-center gap-2">
						{#if authStore.user?.city}
							<span class="flex items-center gap-1 rounded-full bg-cream-dark px-3 py-1 text-xs text-ink-light">
								<svg class="h-3 w-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 13a3 3 0 1 0 0-6 3 3 0 0 0 0 6Z"/><path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7Z"/></svg>
								{authStore.user.city}
							</span>
						{/if}
						{#if authStore.user?.favouriteCuisineDetail}
							<span class="rounded-full bg-jade/10 px-3 py-1 text-xs font-medium text-jade">
								{authStore.user.favouriteCuisineDetail.name}
							</span>
						{/if}
						{#each authStore.user?.dietaryPreferencesDetail ?? [] as pref (pref.id)}
							<span class="rounded-full bg-amber-50 px-3 py-1 text-xs text-amber-700">
								{pref.name}
							</span>
						{/each}
						{#if memberSince}
							<span class="rounded-full bg-cream-dark px-3 py-1 text-xs text-ink-muted">
								{t('profile.since')} {memberSince}
							</span>
						{/if}
					</div>

					{#if authStore.user?.bio}
						<p class="mt-4 max-w-xs text-center text-sm leading-relaxed text-ink-light">{authStore.user.bio}</p>
					{/if}

					<!-- Social links -->
					{#if authStore.user?.instagram || authStore.user?.website}
						<div class="mt-3 flex gap-4">
							{#if authStore.user.instagram}
								<span class="flex items-center gap-1 text-xs text-ink-muted">
									<svg class="h-3.5 w-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="2" width="20" height="20" rx="5" ry="5"/><path d="M16 11.37A4 4 0 1 1 12.63 8 4 4 0 0 1 16 11.37z"/><line x1="17.5" y1="6.5" x2="17.51" y2="6.5"/></svg>
									@{authStore.user.instagram}
								</span>
							{/if}
							{#if authStore.user.website}
								<a href={authStore.user.website} target="_blank" rel="noopener" class="flex items-center gap-1 text-xs text-jade active:opacity-70">
									<svg class="h-3.5 w-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="2" y1="12" x2="22" y2="12"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/></svg>
									Website
								</a>
							{/if}
						</div>
					{/if}
				</div>
			</div>

			<!-- Stats — server-computed in Profile.get_stats; refreshed on mount -->
			{#if authStore.user?.stats}
				<div class="mt-4 flex gap-3">
					<div class="flex-1 rounded-card bg-white p-3 text-center shadow-card">
						<div class="text-xl font-bold text-jade">{authStore.user.stats.pinCount}</div>
						<div class="text-xs text-ink-muted">{t('home.pins')}</div>
					</div>
					<div class="flex-1 rounded-card bg-white p-3 text-center shadow-card">
						<div class="text-xl font-bold text-jade">{authStore.user.stats.visitedCount}</div>
						<div class="text-xs text-ink-muted">{t('common.visited')}</div>
					</div>
					<div class="flex-1 rounded-card bg-white p-3 text-center shadow-card">
						<div class="text-xl font-bold text-jade">{authStore.user.stats.toVisitCount}</div>
						<div class="text-xs text-ink-muted">{t('profile.toVisit')}</div>
					</div>
					<div class="flex-1 rounded-card bg-white p-3 text-center shadow-card">
						<div class="text-xl font-bold text-jade">{authStore.user.stats.friendCount}</div>
						<div class="text-xs text-ink-muted">{t('home.friends')}</div>
					</div>
				</div>
			{/if}

			<!-- My Restaurant Pins -->
			<section class="mt-6">
				<div class="mb-2 flex items-center justify-between">
					<h3 class="text-sm font-semibold uppercase tracking-wide text-ink-muted">{t('profile.myPins')}</h3>
					{#if (authStore.user?.stats?.pinCount ?? 0) > 0}
						<span class="text-xs text-ink-muted">{totalFilteredPins} / {authStore.user?.stats?.pinCount ?? 0}</span>
					{/if}
				</div>

				{#if (authStore.user?.stats?.pinCount ?? 0) > 0}
					<div class="mb-3 flex gap-1 rounded-card bg-cream-dark p-1">
						<button
							onclick={() => setPinsFilter('all')}
							class="flex-1 rounded-button py-1.5 text-xs font-medium active:scale-[0.98]
								{pinsFilter === 'all' ? 'bg-white text-ink shadow-card' : 'text-ink-muted'}"
						>
							{t('common.all')}
						</button>
						<button
							onclick={() => setPinsFilter('visited')}
							class="flex-1 rounded-button py-1.5 text-xs font-medium active:scale-[0.98]
								{pinsFilter === 'visited' ? 'bg-white text-ink shadow-card' : 'text-ink-muted'}"
						>
							{t('common.visited')}
						</button>
						<button
							onclick={() => setPinsFilter('to_visit')}
							class="flex-1 rounded-button py-1.5 text-xs font-medium active:scale-[0.98]
								{pinsFilter === 'to_visit' ? 'bg-white text-ink shadow-card' : 'text-ink-muted'}"
						>
							{t('common.toVisit')}
						</button>
					</div>
				{/if}

				{#if loadingPins}
					<div class="space-y-2">
						{#each Array(2) as _}
							<div class="animate-pulse rounded-card bg-white p-4 shadow-card">
								<div class="h-3 w-3/4 rounded bg-cream-dark"></div>
								<div class="mt-2 h-3 w-1/2 rounded bg-cream-dark"></div>
							</div>
						{/each}
					</div>
				{:else if (authStore.user?.stats?.pinCount ?? 0) === 0}
					<div class="rounded-card bg-white p-5 text-center shadow-card">
						<p class="text-sm text-ink-muted">{t('profile.noPinsYet')}</p>
						<a href="/pin/new" class="mt-2 inline-block text-sm font-medium text-jade active:opacity-70">{t('profile.addFirst')}</a>
					</div>
				{:else if myPins.length === 0}
					<div class="rounded-card bg-white p-5 text-center shadow-card">
						<p class="text-sm text-ink-muted">{t('profile.noPinsMatch')}</p>
					</div>
				{:else}
					<ul class="space-y-2">
						{#each myPins.slice(0, 5) as pin (pin.id)}
							<li>
								<a href={`/restaurant/${pin.restaurantDetail.id}`} class="flex overflow-hidden rounded-card bg-white shadow-card active:scale-[0.98]">
									{#if pin.restaurantDetail.imageUrl}
										<img src={pin.restaurantDetail.imageUrl} alt={pin.restaurantDetail.name} class="h-20 w-16 shrink-0 object-cover" loading="lazy" />
									{/if}
									<div class="flex min-w-0 flex-1 items-center justify-between gap-2 px-3 py-2">
										<div class="min-w-0">
											<p class="truncate text-sm font-semibold text-ink">{pin.restaurantDetail.name}</p>
											{#if pin.restaurantDetail.city}
												<p class="text-xs text-ink-muted">{pin.restaurantDetail.city}</p>
											{/if}
											{#if pin.rating}
												<div class="mt-0.5 flex text-rose-400">
													{#each Array(5) as _, i}
														{#if i < pin.rating}
															<svg class="h-3 w-3" viewBox="0 0 24 24" fill="currentColor"><path d="M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z"/></svg>
														{:else}
															<svg class="h-3 w-3 text-cream-dark" viewBox="0 0 24 24" fill="currentColor"><path d="M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z"/></svg>
														{/if}
													{/each}
												</div>
											{/if}
										</div>
										<span class="shrink-0 rounded-full px-2 py-0.5 text-xs font-medium
											{pin.status === 'visited' ? 'bg-jade/10 text-jade' : 'bg-cream-dark text-ink-muted'}">
											{pin.status === 'visited' ? t('common.visited') : t('common.toVisit')}
										</span>
									</div>
								</a>
							</li>
						{/each}
					</ul>
					{#if totalFilteredPins > 5}
						<a href="/map" class="mt-2 block text-center text-xs font-medium text-jade active:opacity-70">
							{t('profile.viewAllOnMap').replace('{count}', String(totalFilteredPins))}
						</a>
					{/if}
				{/if}
			</section>

			<!-- Share section -->
			<section class="mt-6">
				<h3 class="mb-2 text-sm font-semibold uppercase tracking-wide text-ink-muted">{t('profile.shareList')}</h3>

				{#if sharedLists.length > 0}
					<ul class="space-y-2">
						{#each sharedLists as list (list.id)}
							<li class="flex items-center gap-3 rounded-card bg-white p-4 shadow-card">
								<div class="min-w-0 flex-1">
									<p class="truncate text-sm font-medium text-ink">{list.title || t('profile.myList')}</p>
									<p class="truncate text-xs text-ink-muted">{list.url}</p>
								</div>
								<button onclick={() => copyLink(list.url)} class="flex min-h-9 items-center rounded-button bg-jade/10 px-3 text-xs font-semibold text-jade active:scale-[0.98]">
									{t('profile.copy')}
								</button>
								<button onclick={() => deleteSharedList(list.id)} class="flex min-h-9 items-center rounded-button border border-cream-dark px-3 text-xs font-medium text-ink-muted active:scale-[0.98]">
									{t('profile.remove')}
								</button>
							</li>
						{/each}
					</ul>
				{/if}

				<button
					onclick={createShareLink}
					disabled={sharing}
					class="mt-2 flex min-h-12 w-full items-center justify-center gap-2 rounded-button bg-jade text-base font-semibold text-white active:scale-[0.98] disabled:opacity-50"
				>
					<svg class="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
						<path d="M4 12v8a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-8" /><polyline points="16 6 12 2 8 6" /><line x1="12" y1="2" x2="12" y2="15" />
					</svg>
					{sharing ? t('profile.creating') : t('profile.createShareLink')}
				</button>
			</section>

			<!-- Navigation -->
			<div class="mt-6 space-y-2">
				<a href="/settings" class="flex items-center gap-3 rounded-card bg-white p-4 shadow-card active:scale-[0.98]">
					<div class="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-jade/10 text-jade">
						<svg class="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"/><path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"/></svg>
					</div>
					<span class="flex-1 text-sm font-medium text-ink">{t('settings.title')}</span>
					<svg class="h-4 w-4 text-ink-muted" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="9 18 15 12 9 6"/></svg>
				</a>
			</div>

			<!-- Legal & policies -->
			<section class="mt-6">
				<h3 class="mb-2 text-sm font-semibold uppercase tracking-wide text-ink-muted">{t('legal.section')}</h3>
				<div class="space-y-2">
					<a href="/legal/privacy" class="flex items-center justify-between rounded-card bg-white p-4 shadow-card active:scale-[0.98]">
						<span class="text-sm font-medium text-ink">{t('legal.privacy')}</span>
						<svg class="h-4 w-4 text-ink-muted" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="9 18 15 12 9 6"/></svg>
					</a>
					<a href="/legal/terms" class="flex items-center justify-between rounded-card bg-white p-4 shadow-card active:scale-[0.98]">
						<span class="text-sm font-medium text-ink">{t('legal.terms')}</span>
						<svg class="h-4 w-4 text-ink-muted" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="9 18 15 12 9 6"/></svg>
					</a>
					<a href="/legal/community" class="flex items-center justify-between rounded-card bg-white p-4 shadow-card active:scale-[0.98]">
						<span class="text-sm font-medium text-ink">{t('legal.community')}</span>
						<svg class="h-4 w-4 text-ink-muted" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="9 18 15 12 9 6"/></svg>
					</a>
					<a href="/legal/cookies" class="flex items-center justify-between rounded-card bg-white p-4 shadow-card active:scale-[0.98]">
						<span class="text-sm font-medium text-ink">{t('legal.cookies')}</span>
						<svg class="h-4 w-4 text-ink-muted" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="9 18 15 12 9 6"/></svg>
					</a>
					<a href="/legal/contact" class="flex items-center justify-between rounded-card bg-white p-4 shadow-card active:scale-[0.98]">
						<span class="text-sm font-medium text-ink">{t('legal.contact')}</span>
						<svg class="h-4 w-4 text-ink-muted" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="9 18 15 12 9 6"/></svg>
					</a>
				</div>
			</section>

			<div class="mt-6">
				<button onclick={() => authStore.logout()} class="flex min-h-12 w-full items-center justify-center rounded-button border border-blush text-base font-medium text-blush active:scale-[0.98]">
					{t('auth.signOut')}
				</button>
			</div>

		<!-- ═══ EDIT MODE ═══ -->
		{:else}
			<div class="space-y-4">
				{#if error}
					<div class="rounded-button bg-blush-light/20 px-4 py-3 text-sm text-blush">{error}</div>
				{/if}

				<div class="flex flex-col items-center py-2">
					<Avatar name={editName} src={authStore.user?.avatar} size={80} />
				</div>

				<div>
					<label for="editName" class="mb-1 block text-sm font-medium text-ink-light">{t('auth.displayName')}</label>
					<input id="editName" type="text" bind:value={editName} class="w-full rounded-input border border-cream-dark bg-white px-4 py-3 text-base text-ink outline-none focus:border-jade" placeholder={t('profile.namePlaceholder')} />
				</div>

				<div>
					<label for="editBio" class="mb-1 block text-sm font-medium text-ink-light">{t('profile.bio')}</label>
					<textarea id="editBio" bind:value={editBio} rows="3" maxlength="300" class="w-full rounded-input border border-cream-dark bg-white px-4 py-3 text-base text-ink outline-none focus:border-jade" placeholder={t('profile.bioPlaceholder')}></textarea>
					<p class="mt-1 text-right text-xs text-ink-muted">{editBio.length}/300</p>
				</div>

				<div>
					<label for="editCity" class="mb-1 block text-sm font-medium text-ink-light">{t('profile.cityLabel')}</label>
					<CityAutocomplete bind:value={editCity} placeholder={t('profile.cityPlaceholder')} id="editCity" />
				</div>

				<div class="grid grid-cols-2 gap-3">
					<div>
						<label for="editCuisine" class="mb-1 block text-sm font-medium text-ink-light">{t('profile.favCuisine')}</label>
						<select id="editCuisine" bind:value={editCuisine} class="w-full rounded-input border border-cream-dark bg-white px-4 py-3 text-base text-ink outline-none focus:border-jade">
							<option value="">{t('common.none')}</option>
							{#each cuisines as c}
								<option value={c.id}>{c.name}</option>
							{/each}
						</select>
					</div>
					<div>
						<span class="mb-1 block text-sm font-medium text-ink-light">{t('profile.dietary')}</span>
						<!-- Multi-select chips. Touch-friendly (min-h-11), no hover-dependent
							 affordance, no native multiselect (broken UX on mobile). -->
						<div class="flex flex-wrap gap-2">
							{#each dietaryOptions as opt (opt.id)}
								{@const selected = editDietaryIds.includes(opt.id)}
								<button
									type="button"
									onclick={() => toggleDietary(opt.id)}
									class="min-h-11 rounded-full px-4 text-sm font-medium active:scale-95
										{selected
											? 'bg-jade text-white'
											: 'bg-white text-ink-muted shadow-card'}"
									aria-pressed={selected}
								>
									{opt.name}
								</button>
							{/each}
						</div>
					</div>
				</div>

				<div>
					<label for="editInstagram" class="mb-1 block text-sm font-medium text-ink-light">{t('profile.instagram')}</label>
					<div class="flex items-center rounded-input border border-cream-dark bg-white focus-within:border-jade">
						<span class="pl-4 text-base text-ink-muted">@</span>
						<input id="editInstagram" type="text" bind:value={editInstagram} class="flex-1 bg-transparent px-2 py-3 text-base text-ink outline-none" placeholder={t('profile.instagramPlaceholder')} />
					</div>
				</div>

				<div>
					<label for="editPhone" class="mb-1 block text-sm font-medium text-ink-light">{t('profile.phone')}</label>
					<input id="editPhone" type="tel" bind:value={editPhone} class="w-full rounded-input border border-cream-dark bg-white px-4 py-3 text-base text-ink outline-none focus:border-jade" placeholder={t('profile.phonePlaceholder')} />
				</div>

				<div>
					<label for="editWebsite" class="mb-1 block text-sm font-medium text-ink-light">{t('profile.website')}</label>
					<input id="editWebsite" type="url" bind:value={editWebsite} class="w-full rounded-input border border-cream-dark bg-white px-4 py-3 text-base text-ink outline-none focus:border-jade" placeholder={t('profile.websitePlaceholder')} />
				</div>

				<div class="flex gap-3 pt-2">
					<button onclick={cancelEditing} class="flex min-h-12 flex-1 items-center justify-center rounded-button border border-cream-dark text-base font-medium text-ink-light active:scale-[0.98]">
						{t('profile.cancel')}
					</button>
					<button onclick={saveProfile} disabled={saving} class="flex min-h-12 flex-1 items-center justify-center rounded-button bg-jade text-base font-semibold text-white active:scale-[0.98] disabled:opacity-50">
						{saving ? t('profile.saving') : t('profile.save')}
					</button>
				</div>
			</div>
		{/if}
	</div>
</div>
