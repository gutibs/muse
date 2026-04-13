<script lang="ts">
	import Avatar from '$lib/components/Avatar.svelte';
	import { pinsService } from '$lib/services/pins.service';
	import { restaurantsService } from '$lib/services/restaurants.service';
	import { t } from '$lib/i18n/index.svelte';
	import { authStore } from '$lib/stores/auth.store.svelte';
	import { ApiError } from '$lib/types';
	import type { Cuisine, SharedList } from '$lib/types';

	let editing = $state(false);
	let saving = $state(false);
	let error = $state('');
	let success = $state('');

	// Share
	let sharing = $state(false);
	let sharedLists = $state<SharedList[]>([]);

	// Cuisines for dropdown
	let cuisines = $state<Cuisine[]>([]);

	// Edit fields
	let editName = $state('');
	let editBio = $state('');
	let editCity = $state('');
	let editWebsite = $state('');
	let editInstagram = $state('');
	let editDietary = $state('');
	let editCuisine = $state<number | ''>('');

	const dietaryOptions = ['', 'Omnivore', 'Vegetarian', 'Vegan', 'Pescatarian', 'Halal', 'Kosher', 'Sin TACC', 'Gluten-free'];

	async function loadSharedLists() {
		try { sharedLists = await pinsService.sharedLists(); } catch { sharedLists = []; }
	}

	async function loadCuisines() {
		try { cuisines = await restaurantsService.cuisines(); } catch { cuisines = []; }
	}

	async function createShareLink() {
		sharing = true;
		try {
			const list = await pinsService.createSharedList({ title: `${authStore.user?.displayName}'s List` });
			sharedLists = [...sharedLists, list];
			await navigator.clipboard.writeText(`${window.location.origin}${list.url}`);
			success = 'Link copied to clipboard!';
			setTimeout(() => (success = ''), 3000);
		} catch {
			error = 'Could not create share link.';
		} finally {
			sharing = false;
		}
	}

	async function deleteSharedList(id: number) {
		try {
			await pinsService.deleteSharedList(id);
			sharedLists = sharedLists.filter((l) => l.id !== id);
		} catch {
			error = 'Could not remove link.';
		}
	}

	function copyLink(url: string) {
		navigator.clipboard.writeText(`${window.location.origin}${url}`);
		success = 'Link copied!';
		setTimeout(() => (success = ''), 3000);
	}

	$effect(() => {
		if (authStore.isAuthenticated) {
			loadSharedLists();
			loadCuisines();
		}
	});

	function startEditing() {
		editName = authStore.user?.displayName || '';
		editBio = authStore.user?.bio || '';
		editCity = authStore.user?.city || '';
		editWebsite = authStore.user?.website || '';
		editInstagram = authStore.user?.instagram || '';
		editDietary = authStore.user?.dietary || '';
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
				dietary: editDietary,
				favouriteCuisine: editCuisine || null,
			});
			editing = false;
			success = 'Profile updated';
			setTimeout(() => (success = ''), 3000);
		} catch (err) {
			if (err instanceof ApiError && err.data) {
				const data = err.data as Record<string, string[]>;
				const firstKey = Object.keys(data)[0];
				const messages = data[firstKey];
				error = Array.isArray(messages) ? messages[0] : String(messages);
			} else {
				error = 'Could not update profile.';
			}
		} finally {
			saving = false;
		}
	}

	let memberSince = $derived(
		authStore.user?.createdAt
			? new Date(authStore.user.createdAt).toLocaleDateString('en-GB', { month: 'long', year: 'numeric' })
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
						{authStore.user?.displayName || 'Your Name'}
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
						{#if authStore.user?.dietary}
							<span class="rounded-full bg-amber-50 px-3 py-1 text-xs text-amber-700">
								{authStore.user.dietary}
							</span>
						{/if}
						{#if memberSince}
							<span class="rounded-full bg-cream-dark px-3 py-1 text-xs text-ink-muted">
								Since {memberSince}
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

			<!-- Stats -->
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

			<!-- Share section -->
			<section class="mt-6">
				<h3 class="mb-2 text-sm font-semibold uppercase tracking-wide text-ink-muted">{t('profile.shareList')}</h3>

				{#if sharedLists.length > 0}
					<ul class="space-y-2">
						{#each sharedLists as list (list.id)}
							<li class="flex items-center gap-3 rounded-card bg-white p-4 shadow-card">
								<div class="min-w-0 flex-1">
									<p class="truncate text-sm font-medium text-ink">{list.title || 'My List'}</p>
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
				<a href="/friends" class="flex items-center gap-3 rounded-card bg-white p-4 shadow-card active:scale-[0.98]">
					<div class="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-jade/10 text-jade">
						<svg class="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>
					</div>
					<span class="flex-1 text-sm font-medium text-ink">{t('home.friends')}</span>
					<svg class="h-4 w-4 text-ink-muted" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="9 18 15 12 9 6"/></svg>
				</a>
				<a href="/settings" class="flex items-center gap-3 rounded-card bg-white p-4 shadow-card active:scale-[0.98]">
					<div class="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-jade/10 text-jade">
						<svg class="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"/><path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"/></svg>
					</div>
					<span class="flex-1 text-sm font-medium text-ink">{t('settings.title')}</span>
					<svg class="h-4 w-4 text-ink-muted" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="9 18 15 12 9 6"/></svg>
				</a>
			</div>

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
					<input id="editName" type="text" bind:value={editName} class="w-full rounded-input border border-cream-dark bg-white px-4 py-3 text-base text-ink outline-none focus:border-jade" placeholder="Your name" />
				</div>

				<div>
					<label for="editBio" class="mb-1 block text-sm font-medium text-ink-light">{t('profile.bio')}</label>
					<textarea id="editBio" bind:value={editBio} rows="3" maxlength="300" class="w-full rounded-input border border-cream-dark bg-white px-4 py-3 text-base text-ink outline-none focus:border-jade" placeholder="A bit about you..."></textarea>
					<p class="mt-1 text-right text-xs text-ink-muted">{editBio.length}/300</p>
				</div>

				<div>
					<label for="editCity" class="mb-1 block text-sm font-medium text-ink-light">{t('profile.cityLabel')}</label>
					<input id="editCity" type="text" bind:value={editCity} class="w-full rounded-input border border-cream-dark bg-white px-4 py-3 text-base text-ink outline-none focus:border-jade" placeholder="Where are you based?" />
				</div>

				<div class="grid grid-cols-2 gap-3">
					<div>
						<label for="editCuisine" class="mb-1 block text-sm font-medium text-ink-light">{t('profile.favCuisine')}</label>
						<select id="editCuisine" bind:value={editCuisine} class="w-full rounded-input border border-cream-dark bg-white px-4 py-3 text-base text-ink outline-none focus:border-jade">
							<option value="">None</option>
							{#each cuisines as c}
								<option value={c.id}>{c.name}</option>
							{/each}
						</select>
					</div>
					<div>
						<label for="editDietary" class="mb-1 block text-sm font-medium text-ink-light">{t('profile.dietary')}</label>
						<select id="editDietary" bind:value={editDietary} class="w-full rounded-input border border-cream-dark bg-white px-4 py-3 text-base text-ink outline-none focus:border-jade">
							{#each dietaryOptions as opt}
								<option value={opt}>{opt || 'None'}</option>
							{/each}
						</select>
					</div>
				</div>

				<div>
					<label for="editInstagram" class="mb-1 block text-sm font-medium text-ink-light">{t('profile.instagram')}</label>
					<div class="flex items-center rounded-input border border-cream-dark bg-white focus-within:border-jade">
						<span class="pl-4 text-base text-ink-muted">@</span>
						<input id="editInstagram" type="text" bind:value={editInstagram} class="flex-1 bg-transparent px-2 py-3 text-base text-ink outline-none" placeholder="username" />
					</div>
				</div>

				<div>
					<label for="editWebsite" class="mb-1 block text-sm font-medium text-ink-light">{t('profile.website')}</label>
					<input id="editWebsite" type="url" bind:value={editWebsite} class="w-full rounded-input border border-cream-dark bg-white px-4 py-3 text-base text-ink outline-none focus:border-jade" placeholder="https://..." />
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
