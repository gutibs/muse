<script lang="ts">
	import logoSrc from '$lib/assets/logo_muse.png';

	let {
		width = 120,
	}: {
		width?: number;
	} = $props();
</script>

<img src={logoSrc} alt="Muse" {width} />
