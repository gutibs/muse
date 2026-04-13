<script lang="ts">
	import { browser } from '$app/environment';
	import { page } from '$app/state';
	import Avatar from '$lib/components/Avatar.svelte';
	import MapView from '$lib/components/MapView.svelte';
	import type { SharedListPublic } from '$lib/types';
	import type L from 'leaflet';

	let token = $derived(page.params.token);

	let data = $state<SharedListPublic | null>(null);
	let loading = $state(true);
	let error = $state('');
	let view = $state<'list' | 'map'>('list');

	async function load() {
		loading = true;
		error = '';
		try {
			const API_BASE = import.meta.env.VITE_API_BASE_URL || '/api/v1';
			const res = await fetch(`${API_BASE}/shared/${token}/`);
			if (!res.ok) {
				if (res.status === 404) error = 'This list does not exist or has been removed.';
				else error = 'Could not load list.';
				return;
			}
			data = await res.json();
		} catch {
			error = 'Could not load list.';
		} finally {
			loading = false;
		}
	}

	$effect(() => {
		if (token) load();
	});



	async function onMapReady(map: L.Map) {
		if (!browser || !data?.pins.length) return;

		const leaflet = await import('leaflet');
		const L = leaflet.default;
		const bounds: [number, number][] = [];

		for (const pin of data.pins) {
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
</script>

<div class="flex h-full flex-col bg-cream">
	{#if loading}
		<div class="flex flex-1 items-center justify-center">
			<div class="h-7 w-7 animate-spin rounded-full border-2 border-jade border-t-transparent"></div>
		</div>

	{:else if error}
		<div class="flex flex-1 flex-col items-center justify-center px-6 text-center">
			<p class="text-sm text-blush">{error}</p>
			<a href="/" class="mt-4 text-sm font-medium text-jade active:opacity-70">Go to Muse</a>
		</div>

	{:else if data}
		<header class="shrink-0 px-5 py-4">
			<div class="flex items-center gap-3">
				<Avatar name={data.owner.displayName} src={data.owner.avatar} size={44} />
				<div class="min-w-0 flex-1">
					<h1 class="truncate text-lg font-semibold text-ink">{data.title || `${data.owner.displayName}'s List`}</h1>
					<p class="text-xs text-ink-muted">
						{data.pins.length} restaurant{data.pins.length === 1 ? '' : 's'}
						{#if data.owner.city} · {data.owner.city}{/if}
					</p>
				</div>
			</div>

			<div class="mt-3 flex gap-1 rounded-card bg-cream-dark p-1">
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
		</header>

		<div class="min-h-0 flex-1 overflow-hidden">
			{#if view === 'list'}
				{#if data.pins.length === 0}
					<div class="flex h-full items-center justify-center px-6 text-center">
						<p class="text-sm text-ink-muted">This list is empty</p>
					</div>
				{:else}
					<ul class="h-full space-y-2 overflow-y-auto px-5 pb-6">
						{#each data.pins as pin (pin.id)}
							<li class="flex overflow-hidden rounded-card bg-white shadow-card">
								{#if pin.restaurantDetail.imageUrl}
									<img src={pin.restaurantDetail.imageUrl} alt={pin.restaurantDetail.name} class="h-32 w-24 shrink-0 object-cover" loading="lazy" />
								{/if}
								<div class="flex min-w-0 flex-1 flex-col justify-center gap-1 p-3">
									<div class="flex items-start justify-between gap-2">
										<p class="truncate text-sm font-semibold text-ink">{pin.restaurantDetail.name}</p>
										<span class="shrink-0 rounded-full px-2 py-0.5 text-xs font-medium
											{pin.status === 'visited' ? 'bg-jade/10 text-jade' : 'bg-cream-dark text-ink-muted'}">{pin.status === 'visited' ? 'Visited' : 'To Visit'}</span>
									</div>
									{#if pin.restaurantDetail.city}
										<p class="text-xs text-ink-muted">{pin.restaurantDetail.city}</p>
									{/if}
									{#if pin.rating}
										<div class="flex text-amber-400">
											{#each Array(5) as _, i}
												{#if i < (pin.rating ?? 0)}
													<svg class="h-3.5 w-3.5" viewBox="0 0 20 20" fill="currentColor"><path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z"/></svg>
												{:else}
													<svg class="h-3.5 w-3.5 text-cream-dark" viewBox="0 0 20 20" fill="currentColor"><path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z"/></svg>
												{/if}
											{/each}
										</div>
									{/if}
									{#if pin.comment}
										<p class="line-clamp-2 text-xs italic text-ink-light">"{pin.comment}"</p>
									{/if}
									{#if pin.personasDetail?.length}
										<div class="flex flex-wrap gap-1">
											{#each pin.personasDetail as persona}
												<span class="rounded-full bg-cream-dark px-2 py-0.5 text-xs text-ink-muted">
													{persona.icon} {persona.name}
												</span>
											{/each}
										</div>
									{/if}
								</div>
							</li>
						{/each}
					</ul>
				{/if}
			{:else}
				{#key data.pins.length}
					<MapView center={[20, 0]} zoom={2} autoLocate={false} {onMapReady} />
				{/key}
			{/if}
		</div>

		<!-- Footer CTA -->
		<div class="shrink-0 border-t border-cream-dark bg-white px-5 py-3 text-center">
			<a
				href="/"
				class="inline-flex min-h-11 items-center gap-2 rounded-button bg-jade px-5 text-sm font-semibold text-white active:scale-[0.98]"
			>
				Open Muse
			</a>
		</div>
	{/if}
</div>
