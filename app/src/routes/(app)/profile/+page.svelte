<script lang="ts">
	import Avatar from '$lib/components/Avatar.svelte';
	import { pinsService } from '$lib/services/pins.service';
	import { authStore } from '$lib/stores/auth.store.svelte';
	import { ApiError } from '$lib/types';
	import type { SharedList } from '$lib/types';

	let editing = $state(false);
	let saving = $state(false);
	let error = $state('');
	let success = $state('');

	// Share
	let sharing = $state(false);
	let shareLink = $state('');
	let sharedLists = $state<SharedList[]>([]);

	// Edit fields
	let editName = $state('');
	let editBio = $state('');
	let editCity = $state('');

	async function loadSharedLists() {
		try {
			sharedLists = await pinsService.sharedLists();
		} catch {
			sharedLists = [];
		}
	}

	async function createShareLink() {
		sharing = true;
		shareLink = '';
		try {
			const list = await pinsService.createSharedList({ title: `${authStore.user?.displayName}'s List` });
			shareLink = `${window.location.origin}${list.url}`;
			sharedLists = [...sharedLists, list];
			await navigator.clipboard.writeText(shareLink);
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
		if (authStore.isAuthenticated) loadSharedLists();
	});

	function startEditing() {
		editName = authStore.user?.displayName || '';
		editBio = authStore.user?.bio || '';
		editCity = authStore.user?.city || '';
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
</script>

<div class="flex h-full flex-col">
	<!-- Header -->
	<header class="flex shrink-0 items-center justify-between px-5 py-3">
		<h1 class="text-lg font-semibold text-ink">Profile</h1>
		{#if !editing}
			<button
				onclick={startEditing}
				class="flex min-h-11 items-center gap-1 px-3 text-sm font-medium text-jade active:opacity-70"
			>
				<svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
					<path d="M17 3a2.85 2.83 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5Z" />
					<path d="m15 5 4 4" />
				</svg>
				Edit
			</button>
		{/if}
	</header>

	<div class="flex-1 overflow-y-auto px-5 pb-6">
		<!-- Success toast -->
		{#if success}
			<div class="mb-4 rounded-card bg-jade/10 px-4 py-3 text-sm font-medium text-jade">
				{success}
			</div>
		{/if}

		<!-- Avatar + name -->
		<div class="flex flex-col items-center py-4">
			<Avatar
				name={authStore.user?.displayName || ''}
				src={authStore.user?.avatar}
				size={80}
			/>

			{#if !editing}
				<h2 class="mt-4 font-serif text-2xl font-semibold text-ink">
					{authStore.user?.displayName || 'Your Name'}
				</h2>
				<p class="text-sm text-ink-muted">{authStore.user?.email}</p>
				{#if authStore.user?.city}
					<p class="mt-1 flex items-center gap-1 text-sm text-ink-light">
						<svg class="h-3.5 w-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
							<path d="M12 13a3 3 0 1 0 0-6 3 3 0 0 0 0 6Z" />
							<path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7Z" />
						</svg>
						{authStore.user.city}
					</p>
				{/if}
				{#if authStore.user?.bio}
					<p class="mt-3 max-w-xs text-center text-sm text-ink-light">{authStore.user.bio}</p>
				{/if}
			{/if}
		</div>

		<!-- Stats -->
		{#if authStore.user?.stats}
			<div class="mb-6 flex gap-3">
				<div class="flex-1 rounded-card bg-white p-4 text-center shadow-card">
					<div class="text-2xl font-bold text-jade">{authStore.user.stats.pinCount}</div>
					<div class="text-xs text-ink-muted">Pins</div>
				</div>
				<div class="flex-1 rounded-card bg-white p-4 text-center shadow-card">
					<div class="text-2xl font-bold text-jade">{authStore.user.stats.visitedCount}</div>
					<div class="text-xs text-ink-muted">Visited</div>
				</div>
				<div class="flex-1 rounded-card bg-white p-4 text-center shadow-card">
					<div class="text-2xl font-bold text-jade">{authStore.user.stats.toVisitCount}</div>
					<div class="text-xs text-ink-muted">To Visit</div>
				</div>
				<div class="flex-1 rounded-card bg-white p-4 text-center shadow-card">
					<div class="text-2xl font-bold text-jade">{authStore.user.stats.friendCount}</div>
					<div class="text-xs text-ink-muted">Friends</div>
				</div>
			</div>
		{/if}

		<!-- Edit form -->
		{#if editing}
			<div class="space-y-4">
				{#if error}
					<div class="rounded-button bg-blush-light/20 px-4 py-3 text-sm text-blush">
						{error}
					</div>
				{/if}

				<div>
					<label for="editName" class="mb-1 block text-sm font-medium text-ink-light">Display Name</label>
					<input
						id="editName"
						type="text"
						bind:value={editName}
						class="w-full rounded-input border border-cream-dark bg-white px-4 py-3 text-base text-ink outline-none focus:border-jade"
						placeholder="Your name"
					/>
				</div>

				<div>
					<label for="editEmail" class="mb-1 block text-sm font-medium text-ink-light">Email</label>
					<input
						id="editEmail"
						type="email"
						value={authStore.user?.email || ''}
						disabled
						class="w-full rounded-input border border-cream-dark bg-cream-dark px-4 py-3 text-base text-ink-muted outline-none"
					/>
					<p class="mt-1 text-xs text-ink-muted">Email cannot be changed</p>
				</div>

				<div>
					<label for="editCity" class="mb-1 block text-sm font-medium text-ink-light">City</label>
					<input
						id="editCity"
						type="text"
						bind:value={editCity}
						class="w-full rounded-input border border-cream-dark bg-white px-4 py-3 text-base text-ink outline-none focus:border-jade"
						placeholder="Where are you based?"
					/>
				</div>

				<div>
					<label for="editBio" class="mb-1 block text-sm font-medium text-ink-light">Bio</label>
					<textarea
						id="editBio"
						bind:value={editBio}
						rows="3"
						maxlength="300"
						class="w-full rounded-input border border-cream-dark bg-white px-4 py-3 text-base text-ink outline-none focus:border-jade"
						placeholder="A bit about you..."
					></textarea>
					<p class="mt-1 text-right text-xs text-ink-muted">{editBio.length}/300</p>
				</div>

				<div class="flex gap-3 pt-2">
					<button
						onclick={cancelEditing}
						class="flex min-h-12 flex-1 items-center justify-center rounded-button border border-cream-dark text-base font-medium text-ink-light active:scale-[0.98]"
					>
						Cancel
					</button>
					<button
						onclick={saveProfile}
						disabled={saving}
						class="flex min-h-12 flex-1 items-center justify-center rounded-button bg-jade text-base font-semibold text-white active:scale-[0.98] disabled:opacity-50"
					>
						{saving ? 'Saving...' : 'Save'}
					</button>
				</div>
			</div>
		{/if}

		<!-- Share your list -->
		{#if !editing}
			<section class="mb-6">
				<h3 class="mb-2 text-sm font-semibold uppercase tracking-wide text-ink-muted">Share your list</h3>

				{#if sharedLists.length > 0}
					<ul class="space-y-2">
						{#each sharedLists as list (list.id)}
							<li class="flex items-center gap-3 rounded-card bg-white p-4 shadow-card">
								<div class="min-w-0 flex-1">
									<p class="truncate text-sm font-medium text-ink">{list.title || 'My List'}</p>
									<p class="truncate text-xs text-ink-muted">{list.url}</p>
								</div>
								<button
									onclick={() => copyLink(list.url)}
									class="flex min-h-9 items-center rounded-button bg-jade/10 px-3 text-xs font-semibold text-jade active:scale-[0.98]"
								>
									Copy
								</button>
								<button
									onclick={() => deleteSharedList(list.id)}
									class="flex min-h-9 items-center rounded-button border border-cream-dark px-3 text-xs font-medium text-ink-muted active:scale-[0.98]"
								>
									Remove
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
						<path d="M4 12v8a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-8" />
						<polyline points="16 6 12 2 8 6" />
						<line x1="12" y1="2" x2="12" y2="15" />
					</svg>
					{sharing ? 'Creating...' : 'Create share link'}
				</button>
			</section>
		{/if}

		<!-- Menu items (view mode) -->
		{#if !editing}
			<div class="space-y-2">
				<a
					href="/friends"
					class="flex items-center gap-3 rounded-card bg-white p-4 shadow-card active:scale-[0.98]"
				>
					<div class="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-jade/10 text-jade">
						<svg class="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
							<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" />
							<circle cx="9" cy="7" r="4" />
							<path d="M22 21v-2a4 4 0 0 0-3-3.87" />
							<path d="M16 3.13a4 4 0 0 1 0 7.75" />
						</svg>
					</div>
					<span class="flex-1 text-sm font-medium text-ink">Friends</span>
					<svg class="h-4 w-4 text-ink-muted" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
						<polyline points="9 18 15 12 9 6" />
					</svg>
				</a>

				<a
					href="/settings"
					class="flex items-center gap-3 rounded-card bg-white p-4 shadow-card active:scale-[0.98]"
				>
					<div class="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-jade/10 text-jade">
						<svg class="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
							<circle cx="12" cy="12" r="3" />
							<path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42" />
						</svg>
					</div>
					<span class="flex-1 text-sm font-medium text-ink">Settings</span>
					<svg class="h-4 w-4 text-ink-muted" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
						<polyline points="9 18 15 12 9 6" />
					</svg>
				</a>
			</div>

			<div class="mt-6">
				<button
					onclick={() => authStore.logout()}
					class="flex min-h-12 w-full items-center justify-center rounded-button border border-blush text-base font-medium text-blush active:scale-[0.98]"
				>
					Sign Out
				</button>
			</div>
		{/if}
	</div>
</div>
