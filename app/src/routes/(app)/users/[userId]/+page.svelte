<script lang="ts">
	import { page } from '$app/state';
	import Avatar from '$lib/components/Avatar.svelte';
	import PinsMap, { type MapItem } from '$lib/components/PinsMap.svelte';
	import { t } from '$lib/i18n/index.svelte';
	import { usersService } from '$lib/services/users.service';
	import type { Pin, Profile } from '$lib/types';
	import { ApiError } from '$lib/types';
	import RatingHearts from '$lib/components/RatingHearts.svelte';
	import PinCard from '$lib/components/PinCard.svelte';
	import PinStatusBadge from '$lib/components/PinStatusBadge.svelte';
	import { trackVenueCardView } from '$lib/services/analytics.service';

	let userId = $derived(Number(page.params.userId));

	let profile = $state<Profile | null>(null);
	let pins = $state<Pin[]>([]);
	let loading = $state(true);
	let error = $state('');
	let view = $state<'list' | 'map'>('list');
	let statusFilter = $state<'all' | 'visited' | 'to_visit'>('all');

	async function load() {
		loading = true;
		error = '';
		try {
			const [prof, pinList] = await Promise.all([
				usersService.getProfile(userId),
				usersService.getPins(userId),
			]);
			profile = prof;
			pins = pinList;
		} catch (err) {
			if (err instanceof ApiError && err.status === 403) {
				error = t('users.notFriends');
			} else if (err instanceof ApiError && err.status === 404) {
				error = t('users.notFound');
			} else {
				error = t('users.cantLoad');
			}
		} finally {
			loading = false;
		}
	}

	$effect(() => {
		if (userId) load();
	});

	const filteredPins = $derived(
		statusFilter === 'all' ? pins : pins.filter((p) => p.status === statusFilter)
	);

	const mapItems = $derived<MapItem[]>(
		filteredPins.map((pin) => ({ kind: 'pin' as const, pin }))
	);

	function pinAccent(item: MapItem): 'visited' | 'toVisit' {
		if (item.kind !== 'pin') return 'visited';
		return item.pin.status === 'visited' ? 'visited' : 'toVisit';
	}
</script>

<div class="flex h-full flex-col">
	<!-- Header -->
	<header class="flex shrink-0 items-center gap-3 px-5 py-3">
		<button onclick={() => history.back()} class="flex min-h-11 min-w-11 items-center justify-center text-ink active:opacity-70" aria-label={t('common.back')}>
			<svg class="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
				<polyline points="15 18 9 12 15 6" />
			</svg>
		</button>
		<h1 class="flex-1 text-lg font-semibold text-ink">
			{profile?.displayName || t('common.profile')}
		</h1>
	</header>

	{#if loading}
		<div class="flex flex-1 items-center justify-center">
			<div class="h-7 w-7 animate-spin rounded-full border-2 border-jade border-t-transparent"></div>
		</div>

	{:else if error}
		<div class="flex flex-1 flex-col items-center justify-center px-6 text-center">
			<p class="text-sm text-blush">{error}</p>
			<a href="/friends" class="mt-4 rounded-button bg-jade px-5 py-2.5 text-sm font-semibold text-white active:scale-[0.98]">
				{t('users.backToFriends')}
			</a>
		</div>

	{:else if profile}
		<div class="flex min-h-0 flex-1 flex-col">
			<!-- Profile card -->
			<div class="shrink-0 px-5">
				<div class="flex items-center gap-4 rounded-card bg-white p-4 shadow-card">
					<Avatar name={profile.displayName} src={profile.avatar} size={56} />
					<div class="min-w-0 flex-1">
						<p class="truncate text-base font-semibold text-ink">{profile.displayName || profile.email}</p>
						{#if profile.city}
							<p class="text-xs text-ink-muted">{profile.city}</p>
						{/if}
						{#if profile.bio}
							<p class="mt-1 text-xs italic text-ink-light">{profile.bio}</p>
						{/if}
					</div>
				</div>

				<!-- Stats -->
				<div class="mt-3 flex gap-3">
					<div class="flex-1 rounded-card bg-white p-3 text-center shadow-card">
						<div class="text-xl font-bold text-jade">{profile.stats.pinCount}</div>
						<div class="text-xs text-ink-muted">{t('home.pins')}</div>
					</div>
					<div class="flex-1 rounded-card bg-white p-3 text-center shadow-card">
						<div class="text-xl font-bold text-jade">{profile.stats.visitedCount}</div>
						<div class="text-xs text-ink-muted">{t('users.rated')}</div>
					</div>
					<div class="flex-1 rounded-card bg-white p-3 text-center shadow-card">
						<div class="text-xl font-bold text-jade">{profile.stats.toVisitCount}</div>
						<div class="text-xs text-ink-muted">{t('users.onTheList')}</div>
					</div>
				</div>
			</div>

			<!-- Controls: view toggle + status filter -->
			<div class="mt-4 shrink-0 space-y-2 px-5">
				<div class="flex gap-1 rounded-card bg-cream-dark p-1">
					<button
						onclick={() => (view = 'list')}
						class="flex-1 rounded-button py-2 text-sm font-medium active:scale-[0.98]
							{view === 'list' ? 'bg-white text-ink shadow-card' : 'text-ink-muted'}"
					>
						{t('common.list')}
					</button>
					<button
						onclick={() => (view = 'map')}
						class="flex-1 rounded-button py-2 text-sm font-medium active:scale-[0.98]
							{view === 'map' ? 'bg-white text-ink shadow-card' : 'text-ink-muted'}"
					>
						{t('common.map')}
					</button>
				</div>

				<div class="flex gap-2 overflow-x-auto">
					{#each (['all', 'visited', 'to_visit'] as const) as f}
						<button
							onclick={() => (statusFilter = f)}
							class="shrink-0 rounded-full px-3 py-1.5 text-xs font-medium active:scale-95
								{statusFilter === f ? 'bg-jade text-white' : 'bg-white text-ink-muted shadow-card'}"
						>
							{f === 'all' ? t('common.all') : f === 'visited' ? t('users.rated') : t('users.onTheList')}
						</button>
					{/each}
				</div>
			</div>

			<!-- List or Map -->
			<div class="mt-3 min-h-0 flex-1 overflow-hidden">
				{#if view === 'list'}
					{#if filteredPins.length === 0}
						<div class="flex h-full items-center justify-center px-6 text-center">
							<p class="text-sm text-ink-muted">{t('users.noPins')}</p>
						</div>
					{:else}
						<ul class="h-full space-y-2 overflow-y-auto px-5 pb-6">
							{#each filteredPins as pin (pin.id)}
								<li>
									<PinCard
										onVisible={() => trackVenueCardView(pin.restaurantDetail.id, 'friend')}
										closed={pin.restaurantDetail.isClosed}
										imageUrl={pin.restaurantDetail.imageUrl}
										imageAlt={pin.restaurantDetail.name}
									>
										<div class="flex items-start justify-between gap-2">
											<p class="truncate text-sm font-semibold text-ink">{pin.restaurantDetail.name}</p>
											<PinStatusBadge
												status={pin.status}
												label={pin.status === 'visited' ? t('users.rated') : t('users.onTheList')}
											/>
										</div>
										{#if pin.restaurantDetail.city}
											<p class="text-xs text-ink-muted">{pin.restaurantDetail.city}</p>
										{/if}
										{#if pin.rating}
											<div class="flex items-center gap-1">
												<RatingHearts value={pin.rating} />
											</div>
										{/if}
										{#if pin.comment}
											<p class="line-clamp-2 text-xs italic text-ink-light">"{pin.comment}"</p>
										{/if}
									</PinCard>
								</li>
							{/each}
						</ul>
					{/if}
				{:else}
					<PinsMap
						items={mapItems}
						accent={pinAccent}
						link={false}
						fitOptions={{ padding: [40, 40], maxZoom: 13 }}
					/>
				{/if}
			</div>
		</div>
	{/if}
</div>
