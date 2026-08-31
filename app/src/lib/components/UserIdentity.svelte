<script lang="ts">
	/**
	 * Avatar + nombre + badge, la fila que aparece en cada listado de gente.
	 *
	 * Estaba copiada casi carácter por carácter en cinco pantallas (amigos,
	 * solicitudes, resultados de búsqueda, bloqueados, la cabecera de una
	 * lista compartida) y cada copia tenía su propio tamaño y su propio
	 * fallback. Es la misma historia del glifo del corazón pegado en
	 * diecisiete lugares: mientras el badge no estuviera, la duplicación se
	 * notaba poco; con una marca que puede faltar en una copia y estar en
	 * otra, se lee como que la persona la perdió.
	 */
	import Avatar from './Avatar.svelte';
	import UserName from './UserName.svelte';

	let {
		user,
		size = 44,
		subtitle = '',
		badgeSize = 'sm',
		class: klass = '',
	}: {
		user: {
			displayName?: string;
			avatar?: string | null;
			isDeleted?: boolean;
			isVerifiedInsider?: boolean;
		};
		size?: number;
		/** Ciudad, en general. Se omite sola si viene vacía. */
		subtitle?: string;
		badgeSize?: 'sm' | 'md';
		class?: string;
	} = $props();

	// Una cuenta borrada no muestra su avatar, igual que no muestra su nombre.
	const erased = $derived(user.isDeleted === true);
</script>

<div class="flex min-w-0 items-center gap-3 {klass}">
	<Avatar
		name={erased ? '' : user.displayName}
		src={erased ? null : user.avatar}
		{size}
	/>
	<div class="min-w-0 flex-1">
		<UserName {user} {badgeSize} class="w-full text-sm font-semibold text-ink" />
		{#if subtitle}
			<p class="truncate text-xs text-ink-muted">{subtitle}</p>
		{/if}
	</div>
</div>
