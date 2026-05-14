<script lang="ts">
	import logoSrc from '$lib/assets/logo_muse.png';

	let {
		width = 120,
		href = '',
	}: {
		width?: number;
		href?: string;
	} = $props();
</script>

{#if href}
	<a {href} class="inline-flex active:opacity-70">
		<img src={logoSrc} alt="Muse" {width} />
	</a>
{:else}
	<img src={logoSrc} alt="Muse" {width} />
{/if}
