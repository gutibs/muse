<script lang="ts">
	import Avatar from '$lib/components/Avatar.svelte';
	import { friendsService } from '$lib/services/friends.service';
	import type { Friendship, PublicUser } from '$lib/types';

	type Tab = 'friends' | 'requests' | 'add';

	let tab = $state<Tab>('friends');

	// Friends list
	let friends = $state<Friendship[]>([]);
	let loadingFriends = $state(false);

	// Pending requests
	let requests = $state<Friendship[]>([]);
	let loadingRequests = $state(false);

	// Search / add
	let searchQuery = $state('');
	let searchResults = $state<PublicUser[]>([]);
	let searching = $state(false);
	let searchError = $state('');

	// Email invite
	let inviteEmail = $state('');
	let inviting = $state(false);
	let inviteMessage = $state('');
	let inviteError = $state('');

	// Per-item loading states
	let responding = $state<Record<number, boolean>>({});
	let sending = $state<Record<number, boolean>>({});

	async function loadFriends() {
		loadingFriends = true;
		try {
			friends = await friendsService.list();
		} finally {
			loadingFriends = false;
		}
	}

	async function loadRequests() {
		loadingRequests = true;
		try {
			requests = await friendsService.requests();
		} finally {
			loadingRequests = false;
		}
	}

	async function respond(id: number, status: 'accepted' | 'declined') {
		responding[id] = true;
		try {
			await friendsService.respond(id, status);
			requests = requests.filter((r) => r.id !== id);
			if (status === 'accepted') loadFriends();
		} finally {
			responding[id] = false;
		}
	}

	async function sendRequest(user: PublicUser) {
		sending[user.id] = true;
		searchError = '';
		try {
			await friendsService.sendRequest(user.id);
			searchResults = searchResults.filter((u) => u.id !== user.id);
		} catch (err: unknown) {
			const e = err as { data?: { toUserId?: string[] } };
			searchError = e?.data?.toUserId?.[0] || 'Could not send request.';
		} finally {
			sending[user.id] = false;
		}
	}

	async function doSearch() {
		if (searchQuery.trim().length < 2) return;
		searching = true;
		searchError = '';
		try {
			searchResults = await friendsService.search(searchQuery);
		} finally {
			searching = false;
		}
	}

	let isSearchingSelf = $derived(
		searchQuery.trim().toLowerCase() === (authStore.user?.email ?? '').toLowerCase()
	);

	async function sendInvite() {
		const email = inviteEmail.trim().toLowerCase();
		if (!email) return;

		if (email === (authStore.user?.email ?? '').toLowerCase()) {
			inviteError = "That's your own email.";
			return;
		}

		inviting = true;
		inviteMessage = '';
		inviteError = '';
		try {
			await friendsService.inviteByEmail(email);
			inviteMessage = `Invitation sent to ${email}`;
			inviteEmail = '';
		} catch (err: unknown) {
			const e = err as { data?: { email?: string[] } };
			inviteError = e?.data?.email?.[0] || 'Could not send invite.';
		} finally {
			inviting = false;
		}
	}

	function switchTab(t: Tab) {
		tab = t;
		if (t === 'friends' && friends.length === 0) loadFriends();
		if (t === 'requests') loadRequests();
		if (t === 'add') { searchResults = []; searchQuery = ''; }
	}

	$effect(() => {
		loadFriends();
		loadRequests();
	});

	function getOtherUser(f: Friendship, myId: number): PublicUser {
		return f.fromUser.id === myId ? f.toUser : f.fromUser;
	}

	import { authStore } from '$lib/stores/auth.store.svelte';
	let myId = $derived(authStore.user?.id ?? 0);
</script>

<div class="flex h-full flex-col">
	<header class="shrink-0 px-5 py-4">
		<h1 class="text-lg font-semibold text-ink">Friends</h1>

		<!-- Tabs -->
		<div class="mt-3 flex gap-1 rounded-card bg-cream-dark p-1">
			{#each ([['friends', 'Friends'], ['requests', `Requests${requests.length ? ` (${requests.length})` : ''}`], ['add', 'Add']] as [Tab, string][]) as [t, label]}
				<button
					onclick={() => switchTab(t)}
					class="flex-1 rounded-button py-2 text-sm font-medium transition-colors active:scale-[0.98]
						{tab === t ? 'bg-white text-ink shadow-card' : 'text-ink-muted'}"
				>
					{label}
				</button>
			{/each}
		</div>
	</header>

	<main class="flex-1 overflow-y-auto px-5 pb-6">

		<!-- FRIENDS TAB -->
		{#if tab === 'friends'}
			{#if loadingFriends}
				<div class="flex justify-center py-12">
					<div class="h-6 w-6 animate-spin rounded-full border-2 border-jade border-t-transparent"></div>
				</div>
			{:else if friends.length === 0}
				<div class="flex flex-col items-center py-16 text-center">
					<div class="mb-3 flex h-14 w-14 items-center justify-center rounded-full bg-jade/10 text-jade">
						<svg class="h-7 w-7" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
							<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" />
							<circle cx="9" cy="7" r="4" />
							<path d="M22 21v-2a4 4 0 0 0-3-3.87" />
							<path d="M16 3.13a4 4 0 0 1 0 7.75" />
						</svg>
					</div>
					<p class="text-sm font-medium text-ink">No friends yet</p>
					<p class="mt-1 text-xs text-ink-muted">Search for people or invite by email</p>
					<button
						onclick={() => switchTab('add')}
						class="mt-4 rounded-button bg-jade px-5 py-2.5 text-sm font-semibold text-white active:scale-[0.98]"
					>
						Add Friends
					</button>
				</div>
			{:else}
				<ul class="space-y-2 pt-2">
					{#each friends as friendship (friendship.id)}
						{@const other = getOtherUser(friendship, myId)}
						<li>
							<a
								href={`/users/${other.id}`}
								class="flex items-center gap-3 rounded-card bg-white p-4 shadow-card active:scale-[0.98]"
							>
								<Avatar name={other.displayName} src={other.avatar} size={44} />
								<div class="min-w-0 flex-1">
									<p class="truncate text-sm font-semibold text-ink">{other.displayName || other.email}</p>
									{#if other.city}
										<p class="text-xs text-ink-muted">{other.city}</p>
									{/if}
								</div>
								<svg class="h-4 w-4 text-ink-muted" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
									<polyline points="9 18 15 12 9 6" />
								</svg>
							</a>
						</li>
					{/each}
				</ul>
			{/if}
		{/if}

		<!-- REQUESTS TAB -->
		{#if tab === 'requests'}
			{#if loadingRequests}
				<div class="flex justify-center py-12">
					<div class="h-6 w-6 animate-spin rounded-full border-2 border-jade border-t-transparent"></div>
				</div>
			{:else if requests.length === 0}
				<div class="flex flex-col items-center py-16 text-center">
					<p class="text-sm text-ink-muted">No pending requests</p>
				</div>
			{:else}
				<ul class="space-y-3 pt-2">
					{#each requests as req (req.id)}
						<li class="rounded-card bg-white p-4 shadow-card">
							<div class="flex items-center gap-3">
								<Avatar name={req.fromUser.displayName} src={req.fromUser.avatar} size={44} />
								<div class="min-w-0 flex-1">
									<p class="truncate text-sm font-semibold text-ink">
										{req.fromUser.displayName || req.fromUser.email}
									</p>
									{#if req.fromUser.city}
										<p class="text-xs text-ink-muted">{req.fromUser.city}</p>
									{/if}
								</div>
							</div>
							<div class="mt-3 flex gap-2">
								<button
									onclick={() => respond(req.id, 'declined')}
									disabled={responding[req.id]}
									class="flex min-h-10 flex-1 items-center justify-center rounded-button border border-cream-dark text-sm font-medium text-ink-light active:scale-[0.98] disabled:opacity-50"
								>
									Decline
								</button>
								<button
									onclick={() => respond(req.id, 'accepted')}
									disabled={responding[req.id]}
									class="flex min-h-10 flex-1 items-center justify-center rounded-button bg-jade text-sm font-semibold text-white active:scale-[0.98] disabled:opacity-50"
								>
									{responding[req.id] ? '...' : 'Accept'}
								</button>
							</div>
						</li>
					{/each}
				</ul>
			{/if}
		{/if}

		<!-- ADD TAB -->
		{#if tab === 'add'}
			<div class="space-y-6 pt-2">

				<!-- Search existing users -->
				<div>
					<p class="mb-2 text-sm font-medium text-ink">Search by name or email</p>
					<div class="flex gap-2">
						<input
							type="search"
							bind:value={searchQuery}
							onkeydown={(e) => e.key === 'Enter' && doSearch()}
							placeholder="Search people..."
							class="flex-1 rounded-input border border-cream-dark bg-white px-4 py-3 text-base text-ink outline-none focus:border-jade"
						/>
						<button
							onclick={doSearch}
							disabled={searching || searchQuery.trim().length < 2}
							class="flex min-h-12 items-center rounded-button bg-jade px-4 font-semibold text-white active:scale-[0.98] disabled:opacity-40"
						>
							{#if searching}
								<div class="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent"></div>
							{:else}
								<svg class="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
									<circle cx="11" cy="11" r="8" /><path d="m21 21-4.35-4.35" />
								</svg>
							{/if}
						</button>
					</div>
					{#if searchError}
						<p class="mt-2 text-sm text-blush">{searchError}</p>
					{/if}

					{#if searchResults.length > 0}
						<ul class="mt-3 space-y-2">
							{#each searchResults as user (user.id)}
								<li class="flex items-center gap-3 rounded-card bg-white p-4 shadow-card">
									<Avatar name={user.displayName} src={user.avatar} size={44} />
									<div class="min-w-0 flex-1">
										<p class="truncate text-sm font-semibold text-ink">{user.displayName || user.email}</p>
										{#if user.city}<p class="text-xs text-ink-muted">{user.city}</p>{/if}
									</div>
									<button
										onclick={() => sendRequest(user)}
										disabled={sending[user.id]}
										class="flex min-h-9 items-center rounded-button bg-jade px-3 text-sm font-semibold text-white active:scale-[0.98] disabled:opacity-50"
									>
										{sending[user.id] ? '...' : 'Add'}
									</button>
								</li>
							{/each}
						</ul>
					{:else if isSearchingSelf}
						<p class="mt-3 text-sm text-ink-muted">That's your own email 😄</p>
					{:else if searchQuery.length >= 2 && !searching}
						<p class="mt-3 text-sm text-ink-muted">No users found. Try inviting by email.</p>
					{/if}
				</div>

				<div class="border-t border-cream-dark"></div>

				<!-- Email invite -->
				<div>
					<p class="mb-2 text-sm font-medium text-ink">Invite by email</p>
					<p class="mb-3 text-xs text-ink-muted">Send an invitation to someone not on Muse yet.</p>
					{#if inviteMessage}
						<div class="mb-3 rounded-card bg-jade/10 px-4 py-3 text-sm font-medium text-jade">
							{inviteMessage}
						</div>
					{/if}
					{#if inviteError}
						<p class="mb-2 text-sm text-blush">{inviteError}</p>
					{/if}
					<div class="flex gap-2">
						<input
							type="email"
							bind:value={inviteEmail}
							onkeydown={(e) => e.key === 'Enter' && sendInvite()}
							placeholder="friend@example.com"
							class="flex-1 rounded-input border border-cream-dark bg-white px-4 py-3 text-base text-ink outline-none focus:border-jade"
						/>
						<button
							onclick={sendInvite}
							disabled={inviting || !inviteEmail.trim()}
							class="flex min-h-12 items-center rounded-button bg-jade px-4 text-sm font-semibold text-white active:scale-[0.98] disabled:opacity-40"
						>
							{inviting ? '...' : 'Invite'}
						</button>
					</div>
				</div>
			</div>
		{/if}

	</main>
</div>
