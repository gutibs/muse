<script lang="ts">
	/**
	 * El nombre de una persona, con su fallback y su badge.
	 *
	 * El fallback estaba escrito a mano en ocho pantallas —`displayName ||
	 * t('restaurant.anonymous')`— y en una novena divergía usando el email,
	 * que además el backend ya no manda. Acá vive una sola vez.
	 *
	 * Existe aparte de `UserIdentity` porque en el feed, en home y en la ficha
	 * de restaurante el nombre va incrustado en una frase o en una fila con
	 * otras cosas, no arriba de un avatar. Forzar la fila entera en esos
	 * lugares deformaría tres pantallas para reusar un componente.
	 */
	import { t } from '$lib/i18n/index.svelte';
	import InsiderBadge from './InsiderBadge.svelte';

	let {
		user,
		badge = true,
		badgeSize = 'sm',
		class: klass = '',
	}: {
		user: { displayName?: string; isDeleted?: boolean; isVerifiedInsider?: boolean };
		/** En una frase corrida el glifo estorba; ahí se apaga. */
		badge?: boolean;
		badgeSize?: 'sm' | 'md';
		class?: string;
	} = $props();

	// Una cuenta borrada no lleva nombre ni marca: el borrado destruye la
	// identidad, y el badge es identidad.
	const erased = $derived(user.isDeleted === true);
	const label = $derived(erased ? t('restaurant.anonymous') : user.displayName || t('restaurant.anonymous'));
	const showBadge = $derived(badge && !erased && user.isVerifiedInsider === true);
</script>

<span class="inline-flex min-w-0 items-center gap-1 {klass}">
	<span class="truncate">{label}</span>
	{#if showBadge}
		<InsiderBadge size={badgeSize} />
	{/if}
</span>
