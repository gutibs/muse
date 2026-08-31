<script lang="ts">
	/**
	 * Qué significa cada marca de la app.
	 *
	 * Existe porque el Verified Insider aparece como un glifo suelto en las
	 * pantallas densas, y un ícono que nadie puede descifrar no informa: sólo
	 * decora. Cubre todas las marcas y no sólo esa —el chip de amistad, los
	 * estados de un pin, la estrella, los niveles de privacidad y las
	 * dietarias— porque la pregunta que se hace alguien no es "qué es este
	 * ícono" sino "qué son todos estos íconos".
	 */
	import HeartIcon from '$lib/components/HeartIcon.svelte';
	import InsiderBadge from '$lib/components/InsiderBadge.svelte';
	import PinStatusBadge from '$lib/components/PinStatusBadge.svelte';
	import StarIcon from '$lib/components/StarIcon.svelte';
	import { t } from '$lib/i18n/index.svelte';
	import { goto } from '$app/navigation';

	function goBack() {
		if (history.length > 1) history.back();
		else goto('/settings');
	}
</script>

<div class="flex h-full flex-col">
	<header class="flex shrink-0 items-center gap-3 px-4 py-3">
		<!-- Vuelve a donde estabas y no a una pantalla fija: acá se llega desde
		     Ajustes y desde el badge del propio perfil. Con `/badges` abierta
		     directo por URL no hay a dónde volver, y ahí sí va Ajustes. -->
		<button
			onclick={goBack}
			class="flex min-h-11 min-w-11 items-center justify-center rounded-lg active:scale-95"
			aria-label={t('common.back')}
		>
			<svg
				class="h-6 w-6 text-ink"
				viewBox="0 0 24 24"
				fill="none"
				stroke="currentColor"
				stroke-width="2"
				stroke-linecap="round"
				stroke-linejoin="round"
			>
				<polyline points="15 18 9 12 15 6" />
			</svg>
		</button>
		<h1 class="text-lg font-semibold text-ink">{t('badges.title')}</h1>
	</header>

	<main class="flex-1 overflow-y-auto px-5 pb-8">
		<p class="text-sm leading-relaxed text-ink-light">{t('badges.intro')}</p>

		<!-- Personas -->
		<section class="mt-6">
			<h2 class="text-xs font-semibold uppercase tracking-wide text-ink-muted">
				{t('badges.people')}
			</h2>
			<ul class="mt-2 space-y-2">
				<li class="rounded-card bg-white p-4 shadow-card">
					<InsiderBadge variant="full" />
					<p class="mt-2 text-sm leading-relaxed text-ink-light">{t('badges.insiderWhat')}</p>
				</li>
				<li class="rounded-card bg-white p-4 shadow-card">
					<span
						class="rounded-full bg-jade/10 px-1.5 py-0.5 text-[9px] font-medium uppercase text-jade"
					>
						{t('restaurant.friendBadge')}
					</span>
					<p class="mt-2 text-sm leading-relaxed text-ink-light">{t('badges.friendWhat')}</p>
				</li>
			</ul>
		</section>

		<!-- Pins -->
		<section class="mt-6">
			<h2 class="text-xs font-semibold uppercase tracking-wide text-ink-muted">
				{t('badges.pins')}
			</h2>
			<ul class="mt-2 space-y-2">
				<li class="rounded-card bg-white p-4 shadow-card">
					<PinStatusBadge status="visited" label={t('common.visited')} />
					<p class="mt-2 text-sm leading-relaxed text-ink-light">{t('badges.visitedWhat')}</p>
				</li>
				<li class="rounded-card bg-white p-4 shadow-card">
					<PinStatusBadge status="to_visit" label={t('common.toVisit')} />
					<p class="mt-2 text-sm leading-relaxed text-ink-light">{t('badges.toVisitWhat')}</p>
				</li>
				<li class="rounded-card bg-white p-4 shadow-card">
					<span class="inline-flex items-center gap-1.5 text-sm font-medium text-gold">
						<StarIcon size="sm" filled={true} />
						{t('pin.favourite')}
					</span>
					<p class="mt-2 text-sm leading-relaxed text-ink-light">{t('badges.favouriteWhat')}</p>
				</li>
				<li class="rounded-card bg-white p-4 shadow-card">
					<span class="inline-flex items-center gap-1.5 text-sm font-medium text-blush">
						<HeartIcon class="h-4 w-4" />
						{t('pin.rating')}
					</span>
					<p class="mt-2 text-sm leading-relaxed text-ink-light">{t('badges.ratingWhat')}</p>
				</li>
			</ul>
		</section>

		<!-- Privacidad -->
		<section class="mt-6">
			<h2 class="text-xs font-semibold uppercase tracking-wide text-ink-muted">
				{t('badges.privacy')}
			</h2>
			<ul class="mt-2 space-y-2">
				<li class="rounded-card bg-white p-4 shadow-card">
					<span class="text-sm font-medium text-ink">{t('pin.visibility.public')}</span>
					<p class="mt-1 text-sm leading-relaxed text-ink-light">{t('badges.publicWhat')}</p>
				</li>
				<li class="rounded-card bg-white p-4 shadow-card">
					<span class="text-sm font-medium text-ink">{t('pin.visibility.friends')}</span>
					<p class="mt-1 text-sm leading-relaxed text-ink-light">{t('badges.friendsWhat')}</p>
				</li>
				<li class="rounded-card bg-white p-4 shadow-card">
					<span class="text-sm font-medium text-ink">{t('pin.visibility.private')}</span>
					<p class="mt-1 text-sm leading-relaxed text-ink-light">{t('badges.privateWhat')}</p>
				</li>
			</ul>
		</section>

		<!-- Dietarias -->
		<section class="mt-6">
			<h2 class="text-xs font-semibold uppercase tracking-wide text-ink-muted">
				{t('badges.food')}
			</h2>
			<div class="mt-2 rounded-card bg-white p-4 shadow-card">
				<span class="rounded-full bg-amber-50 px-2 py-0.5 text-xs font-medium text-amber-700">
					{t('badges.dietaryExample')}
				</span>
				<p class="mt-2 text-sm leading-relaxed text-ink-light">{t('badges.dietaryWhat')}</p>
			</div>
		</section>
	</main>
</div>
