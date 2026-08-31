<script lang="ts">
	import { tagLabel } from '$lib/utils/taxonomy';
	import { page } from '$app/state';
	import Avatar from '$lib/components/Avatar.svelte';
	import InsiderBadge from '$lib/components/InsiderBadge.svelte';
	import PinsMap, { type MapItem } from '$lib/components/PinsMap.svelte';
	import { t } from '$lib/i18n/index.svelte';
	import type { SharedListPublic } from '$lib/types';
	import { logSilent } from '$lib/utils/logger';
	import RatingHearts from '$lib/components/RatingHearts.svelte';
	import PinCard from '$lib/components/PinCard.svelte';
	import PinStatusBadge from '$lib/components/PinStatusBadge.svelte';

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
				if (res.status === 404) error = t('shared.notExist');
				else error = t('shared.cantLoad');
				return;
			}
			data = await res.json();
		} catch (err) {
			error = t('shared.cantLoad');
			logSilent('shared:load', err);
		} finally {
			loading = false;
		}
	}

	$effect(() => {
		if (token) load();
	});

	const mapItems = $derived<MapItem[]>(
		(data?.pins ?? []).map((pin) => ({ kind: 'pin' as const, pin }))
	);

	function pinAccent(item: MapItem): 'visited' | 'toVisit' {
		if (item.kind !== 'pin') return 'visited';
		return item.pin.status === 'visited' ? 'visited' : 'toVisit';
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
			<a href="/" class="mt-4 text-sm font-medium text-jade active:opacity-70">{t('shared.goToMuse')}</a>
		</div>

	{:else if data}
		<header class="shrink-0 px-5 py-4">
			<div class="flex items-center gap-3">
				<Avatar name={data.owner.displayName} src={data.owner.avatar} size={44} />
				<div class="min-w-0 flex-1">
					<h1 class="truncate text-lg font-semibold text-ink">{data.title || t('shared.someoneList').replace('{name}', data.owner.displayName || '')}</h1>
					<p class="text-xs text-ink-muted">
						{(data.pins.length === 1 ? t('shared.restaurants') : t('shared.restaurantsPlural')).replace('{count}', String(data.pins.length))}
						{#if data.owner.city} · {data.owner.city}{/if}
					</p>
				</div>
			</div>

			<!-- Acá el badge va con el nombre y la explicación al lado, no como
			     glifo suelto: quien abre este link puede no tener cuenta, y es
			     el lector con menos contexto de todos para descifrar un ícono. -->
			{#if data.owner.isVerifiedInsider}
				<div class="mt-3 flex items-start gap-2 rounded-card bg-jade-dark/5 px-3 py-2">
					<InsiderBadge variant="full" class="shrink-0" />
					<p class="text-xs leading-snug text-ink-light">{t('badges.insiderWhat')}</p>
				</div>
			{/if}

			<div class="mt-3 flex gap-1 rounded-card bg-cream-dark p-1">
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
		</header>

		<div class="min-h-0 flex-1 overflow-hidden">
			{#if view === 'list'}
				{#if data.pins.length === 0}
					<div class="flex h-full items-center justify-center px-6 text-center">
						<p class="text-sm text-ink-muted">{t('shared.empty')}</p>
					</div>
				{:else}
					<ul class="h-full space-y-2 overflow-y-auto px-5 pb-6">
						<!-- Keyed by restaurant, not pin: the public payload withholds the
						     pin id, and (user, restaurant) is unique so it is just as stable. -->
						{#each data.pins as pin (pin.restaurantDetail.id)}
							<li>
								<PinCard
									imageUrl={pin.restaurantDetail.imageUrl}
									imageAlt={pin.restaurantDetail.name}
									imageClass="h-32 w-24"
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
										<RatingHearts value={(pin.rating ?? 0)} />
									{/if}
									{#if pin.note}
										<!-- Nota escrita para esta lista en particular. Va antes del
										     comentario del pin porque es lo que el dueño quiso decir
										     de este lugar a quien recibe el link. -->
										<p class="text-xs font-medium text-jade-dark">{pin.note}</p>
									{/if}
									{#if pin.comment}
										<p class="line-clamp-2 text-xs italic text-ink-light">"{pin.comment}"</p>
									{/if}
									{#if pin.tagsDetail?.length}
										<div class="flex flex-wrap gap-1">
											{#each pin.tagsDetail as tag}
												<span class="rounded-full bg-cream-dark px-2 py-0.5 text-xs text-ink-muted">
													{tagLabel(tag)}
												</span>
											{/each}
										</div>
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

		<!-- Footer CTA -->
		<div class="shrink-0 border-t border-cream-dark bg-white px-5 py-3 text-center">
			<a
				href="/register"
				class="inline-flex min-h-11 items-center gap-2 rounded-button bg-jade px-5 text-sm font-semibold text-white active:scale-[0.98]"
			>
				{t('shared.joinMuse')}
			</a>
		</div>
	{/if}
</div>
