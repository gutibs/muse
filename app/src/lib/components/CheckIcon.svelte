<script lang="ts">
	/**
	 * El tick. Es el ícono del voto —decisión de producto: la estrella es
	 * favoritos y el corazón es el rating— y el único lugar con este glifo.
	 *
	 * De trazo y no relleno, como el resto de los íconos del producto: un
	 * check sólido al lado de un corazón y una estrella de línea se ve
	 * pegado de otro lado.
	 */
	let {
		size = 'md',
		class: klass = '',
	}: {
		size?: 'sm' | 'md';
		class?: string;
	} = $props();

	const SIZES = { sm: 'h-4 w-4', md: 'h-5 w-5' };
</script>

<svg
	class="{SIZES[size]} {klass}"
	viewBox="0 0 24 24"
	fill="none"
	stroke="currentColor"
	stroke-width="2.4"
	stroke-linecap="round"
	stroke-linejoin="round"
	aria-hidden="true"
>
	<polyline points="20 6 9 17 4 12" />
</svg>
