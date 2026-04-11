<script lang="ts">
	import { browser } from '$app/environment';
	import { page } from '$app/state';
	import Avatar from '$lib/components/Avatar.svelte';
	import MapView from '$lib/components/MapView.svelte';
	import { usersService } from '$lib/services/users.service';
	import type { Pin, Profile } from '$lib/types';
	import { ApiError } from '$lib/types';
	import type L from 'leaflet';

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
				error = 'You need to be friends with this user to see their pins.';
			} else if (err instanceof ApiError && err.status === 404) {
				error = 'User not found.';
			} else {
				error = 'Could not load user.';
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

	async function onMapReady(map: L.Map) {
		if (!browser || filteredPins.length === 0) return;

		const leaflet = await import('leaflet');
		const L = leaflet.default;

		const bounds: [number, number][] = [];

		for (const pin of filteredPins) {
			const r = pin.restaurantDetail;
			if (!r?.lat || !r?.lng) continue;

			const color = pin.status === 'visited' ? '#2D6A4F' : '#8A8A8A';
			const icon = L.divIcon({
				className: '',
				html: `<div style="width:28px;height:28px;background:${color};border:3px solid white;border-radius:50%;box-shadow:0 2px 6px rgba(0,0,0,0.2);"></div>`,
				iconSize: [28, 28],
				iconAnchor: [14, 14],
			});

			L.marker([r.lat, r.lng], { icon })
				.addTo(map)
				.bindPopup(`
					<div style="font-family:Inter,sans-serif;min-width:140px;">
						<strong style="font-size:14px;">${r.name}</strong>
						${r.city ? `<br><span style="color:#8A8A8A;font-size:12px;">${r.city}</span>` : ''}
						${pin.rating ? `<br><span style="color:#2D6A4F;font-size:13px;">★ ${pin.rating}/5</span>` : ''}
					</div>
				`);

			bounds.push([r.lat, r.lng]);
		}

		if (bounds.length > 0) {
			map.fitBounds(bounds, { padding: [40, 40], maxZoom: 13 });
		}
	}

	function stars(n: number | null): string {
		if (!n) return '';
		return '★'.repeat(n) + '☆'.repeat(5 - n);
	}
</script>

<div class="flex h-full flex-col">
	<!-- Header -->
	<header class="flex shrink-0 items-center gap-3 px-5 py-3">
		<a href="/friends" class="flex min-h-11 min-w-11 items-center justify-center text-ink active:opacity-70" aria-label="Back">
			<svg class="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
				<polyline points="15 18 9 12 15 6" />
			</svg>
		</a>
		<h1 class="flex-1 text-lg font-semibold text-ink">
			{profile?.displayName || 'Profile'}
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
				Back to Friends
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
						<div class="text-xs text-ink-muted">Pins</div>
					</div>
					<div class="flex-1 rounded-card bg-white p-3 text-center shadow-card">
						<div class="text-xl font-bold text-jade">{profile.stats.visitedCount}</div>
						<div class="text-xs text-ink-muted">Visited</div>
					</div>
					<div class="flex-1 rounded-card bg-white p-3 text-center shadow-card">
						<div class="text-xl font-bold text-jade">{profile.stats.toVisitCount}</div>
						<div class="text-xs text-ink-muted">To Visit</div>
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
						List
					</button>
					<button
						onclick={() => (view = 'map')}
						class="flex-1 rounded-button py-2 text-sm font-medium active:scale-[0.98]
							{view === 'map' ? 'bg-white text-ink shadow-card' : 'text-ink-muted'}"
					>
						Map
					</button>
				</div>

				<div class="flex gap-2 overflow-x-auto">
					{#each (['all', 'visited', 'to_visit'] as const) as f}
						<button
							onclick={() => (statusFilter = f)}
							class="shrink-0 rounded-full px-3 py-1.5 text-xs font-medium active:scale-95
								{statusFilter === f ? 'bg-jade text-white' : 'bg-white text-ink-muted shadow-card'}"
						>
							{f === 'all' ? 'All' : f === 'visited' ? 'Visited' : 'To Visit'}
						</button>
					{/each}
				</div>
			</div>

			<!-- List or Map -->
			<div class="mt-3 min-h-0 flex-1 overflow-hidden">
				{#if view === 'list'}
					{#if filteredPins.length === 0}
						<div class="flex h-full items-center justify-center px-6 text-center">
							<p class="text-sm text-ink-muted">No pins to show</p>
						</div>
					{:else}
						<ul class="h-full space-y-2 overflow-y-auto px-5 pb-6">
							{#each filteredPins as pin (pin.id)}
								<li class="rounded-card bg-white p-4 shadow-card">
									<div class="flex items-start justify-between gap-3">
										<div class="min-w-0 flex-1">
											<p class="truncate text-sm font-semibold text-ink">{pin.restaurantDetail.name}</p>
											{#if pin.restaurantDetail.city}
												<p class="text-xs text-ink-muted">{pin.restaurantDetail.city}</p>
											{/if}
											{#if pin.rating}
												<p class="mt-1 text-sm tracking-tight text-amber-500">{stars(pin.rating)}</p>
											{/if}
											{#if pin.comment}
												<p class="mt-1 text-xs italic text-ink-light">"{pin.comment}"</p>
											{/if}
										</div>
										<span class="shrink-0 rounded-full px-2 py-0.5 text-xs font-medium
											{pin.status === 'visited' ? 'bg-jade/10 text-jade' : 'bg-cream-dark text-ink-muted'}">
											{pin.status === 'visited' ? 'Visited' : 'To Visit'}
										</span>
									</div>
								</li>
							{/each}
						</ul>
					{/if}
				{:else}
					{#key filteredPins.length + '-' + statusFilter}
						<MapView center={[20, 0]} zoom={2} autoLocate={false} {onMapReady} />
					{/key}
				{/if}
			</div>
		</div>
	{/if}
</div>
