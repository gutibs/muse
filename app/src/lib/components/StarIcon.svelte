<script lang="ts">
	/**
	 * La estrella de favoritos. Componente propio y no una variante de
	 * `HeartIcon`: el corazón ya significa el rating, y dos significados en
	 * el mismo glifo se confunden en una tarjeta donde conviven.
	 */
	let {
		filled = false,
		size = 'md',
		class: klass = '',
	}: {
		filled?: boolean;
		size?: 'sm' | 'md';
		class?: string;
	} = $props();

	const SIZES = { sm: 'h-4 w-4', md: 'h-5 w-5' };
</script>

<svg
	class="{SIZES[size]} {klass}"
	viewBox="0 0 24 24"
	fill={filled ? 'currentColor' : 'none'}
	stroke="currentColor"
	stroke-width="1.8"
	stroke-linecap="round"
	stroke-linejoin="round"
	aria-hidden="true"
>
	<polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2" />
</svg>
