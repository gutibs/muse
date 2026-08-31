<script lang="ts">
	import { tagLabel } from '$lib/utils/taxonomy';
	import Avatar from '$lib/components/Avatar.svelte';
	import InsiderBadge from '$lib/components/InsiderBadge.svelte';
	import UserName from '$lib/components/UserName.svelte';
	import { feedService } from '$lib/services/feed.service';
	import { t } from '$lib/i18n/index.svelte';
	import type { Activity } from '$lib/types';
	import { timeAgo } from '$lib/utils/time';
	import { logSilent } from '$lib/utils/logger';
	import RatingHearts from '$lib/components/RatingHearts.svelte';

	let activities = $state<Activity[]>([]);
	let loading = $state(true);
	let loadingMore = $state(false);
	let nextPage = $state<number | null>(null);
	let error = $state('');
	let insiderOnly = $state(false);

	function toggleInsiderOnly() {
		insiderOnly = !insiderOnly;
		// Se recarga desde la primera página: el filtro cambia el conjunto, y
		// seguir paginando el anterior mezclaría dos listas distintas.
		load(1);
	}

	async function load(page = 1) {
		if (page === 1) loading = true;
		else loadingMore = true;
		error = '';
		try {
			const res = await feedService.list(page, insiderOnly);
			if (page === 1) activities = res.results;
			else activities = [...activities, ...res.results];
			nextPage = res.next ? page + 1 : null;
		} catch (err) {
			error = t('home.cantLoad');
			logSilent('feed:load', err);
		} finally {
			loading = false;
			loadingMore = false;
		}
	}

	$effect(() => { load(1); });

	function verbLabel(a: Activity): string {
		switch (a.verb) {
			case 'pinned': return t('feed.wantsToVisit');
			case 'rated': return t('feed.visited');
			case 'updated': return t('feed.updated');
			case 'friendship': return t('feed.becameFriends');
			case 'joined': return t('feed.joinedMuse');
			default: return '';
		}
	}

</script>

<div class="flex h-full flex-col">
	<header class="shrink-0 px-5 py-4">
		<h1 class="text-lg font-semibold text-ink">{t('feed.title')}</h1>
		<p class="text-xs text-ink-muted">{t('feed.subtitle')}</p>
	</header>

	<main class="flex-1 overflow-y-auto px-5 pb-6">
		<!-- Primer filtro de esta pantalla. Va dentro del main y no en el
		     header para que scrollee con la lista: en el header comería alto
		     útil en cada pantalla de teléfono. -->
		<div class="pb-3">
			<button
				onclick={toggleInsiderOnly}
				aria-pressed={insiderOnly}
				class="flex w-fit items-center gap-1.5 rounded-full px-3 py-1.5 text-xs font-medium active:scale-95
					{insiderOnly ? 'bg-jade-dark text-white' : 'border border-cream-dark bg-white text-ink-muted'}"
			>
				<InsiderBadge size="sm" labelled={false} tone={insiderOnly ? 'inherit' : 'brand'} />
				{t('feed.onlyInsiders')}
			</button>
		</div>

		{#if loading}
			<div class="flex justify-center py-16">
				<div class="h-7 w-7 animate-spin rounded-full border-2 border-jade border-t-transparent"></div>
			</div>

		{:else if error}
			<div class="flex flex-col items-center py-16 text-center">
				<p class="text-sm text-blush">{error}</p>
				<button onclick={() => load(1)} class="mt-3 text-sm font-medium text-jade active:opacity-70">
					{t('feed.tryAgain')}
				</button>
			</div>

		{:else if activities.length === 0}
			<div class="flex flex-col items-center py-16 text-center">
				<div class="mb-3 flex h-14 w-14 items-center justify-center rounded-full bg-jade/10 text-jade">
					<svg class="h-7 w-7" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
						<path d="M3 2v7c0 1.1.9 2 2 2h4a2 2 0 0 0 2-2V2"/><path d="M7 2v20"/><path d="M21 15V2v0a5 5 0 0 0-5 5v6c0 1.1.9 2 2 2h3Zm0 0v7"/>
					</svg>
				</div>
				<!-- Con el filtro puesto, "no tenés amigos todavía" es falso y
				     manda a la pantalla equivocada: lo que falta es actividad de
				     Insiders, y el camino es apagar el filtro. -->
				{#if insiderOnly}
					<p class="text-sm font-medium text-ink">{t('feed.emptyInsiders')}</p>
					<button
						onclick={toggleInsiderOnly}
						class="mt-4 rounded-button bg-jade px-5 py-2.5 text-sm font-semibold text-white active:scale-[0.98]"
					>
						{t('feed.showAll')}
					</button>
				{:else}
					<p class="text-sm font-medium text-ink">{t('feed.empty')}</p>
					<p class="mt-1 text-xs text-ink-muted">{t('feed.emptyDesc')}</p>
					<a
						href="/friends"
						class="mt-4 rounded-button bg-jade px-5 py-2.5 text-sm font-semibold text-white active:scale-[0.98]"
					>
						{t('feed.findFriends')}
					</a>
				{/if}
			</div>

		{:else}
			<ul class="space-y-3">
				{#each activities as activity (activity.id)}
					<li class="rounded-card bg-white p-4 shadow-card">
						<div class="flex items-start gap-3">
							<a href={`/users/${activity.actor.id}`} class="shrink-0">
								<Avatar
									name={activity.actor.displayName}
									src={activity.actor.avatar}
									size={40}
								/>
							</a>
							<div class="min-w-0 flex-1">
								<!-- Main line -->
								<p class="text-sm text-ink">
									<a href={`/users/${activity.actor.id}`} class="font-semibold text-ink active:text-jade"><UserName user={activity.actor} /></a>
									{' '}
									{#if activity.verb === 'joined'}
										<span class="text-ink-muted">{t('feed.joinedMuse')} 🎉</span>
									{:else if activity.verb === 'friendship' && activity.targetUser}
										<span class="text-ink-muted">{t('feed.becameFriends')}</span>
										{' '}
										<span class="font-semibold"><UserName user={activity.targetUser} /></span>
									{:else if activity.verb === 'pinned' && activity.pin}
										{@const parts = t('feed.wantsToVisit').split('{restaurant}')}
										<span class="text-ink-muted">{parts[0]}</span><a href={`/map?focus=${activity.pin.restaurantDetail.id}`} class="font-semibold text-ink active:text-jade">{activity.pin.restaurantDetail.name}</a><span class="text-ink-muted">{activity.pin.restaurantDetail.city ? `, ${activity.pin.restaurantDetail.city}` : ''}{parts[1] || ''}</span>
									{:else if activity.pin}
										<span class="text-ink-muted">{verbLabel(activity)}&nbsp;</span><a href={`/map?focus=${activity.pin.restaurantDetail.id}`} class="font-semibold text-ink active:text-jade">{activity.pin.restaurantDetail.name}</a>{#if activity.pin.restaurantDetail.city}<span class="text-ink-muted">, {activity.pin.restaurantDetail.city}</span>{/if}
									{/if}
								</p>

								<!-- Rating -->
								{#if activity.verb === 'rated' && activity.pin?.rating}
									<RatingHearts value={activity.pin.rating} class="mt-0.5" />
								{/if}

								<!-- Comment -->
								{#if activity.pin?.comment}
									<p class="mt-1 text-xs italic text-ink-muted">"{activity.pin.comment}"</p>
								{/if}

								<!-- Etiquetas del pin (vibe / ocasión / características) -->
								{#if activity.pin?.tagsDetail?.length}
									<div class="mt-1.5 flex flex-wrap gap-1">
										{#each activity.pin.tagsDetail as tag}
											<span class="rounded-full bg-cream-dark px-2 py-0.5 text-xs text-ink-muted">
												{tagLabel(tag)}
											</span>
										{/each}
									</div>
								{/if}

								<!-- Timestamp -->
								<p class="mt-1.5 text-xs text-ink-muted">{timeAgo(activity.createdAt)}</p>
							</div>
						</div>
					</li>
				{/each}
			</ul>

			{#if nextPage}
				<div class="mt-4 flex justify-center">
					<button
						onclick={() => load(nextPage!)}
						disabled={loadingMore}
						class="flex min-h-11 items-center gap-2 rounded-button border border-cream-dark px-5 text-sm font-medium text-ink-muted active:scale-[0.98] disabled:opacity-50"
					>
						{#if loadingMore}
							<div class="h-4 w-4 animate-spin rounded-full border-2 border-jade border-t-transparent"></div>
						{:else}
							{t('feed.loadMore')}
						{/if}
					</button>
				</div>
			{/if}
		{/if}
	</main>
</div>
