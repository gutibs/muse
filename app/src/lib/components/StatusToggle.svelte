<script lang="ts">
	import SegmentedControl from '$lib/components/SegmentedControl.svelte';
	import type { PinStatus } from '$lib/types';
	import { t } from '$lib/i18n/index.svelte';

	let { value = $bindable('to_visit') }: { value: PinStatus } = $props();

	// `$derived` y no una constante: el idioma se cambia en caliente desde
	// Ajustes y las etiquetas tienen que seguirlo.
	const options = $derived([
		{ value: 'to_visit' as PinStatus, label: t('common.toVisit') },
		{ value: 'visited' as PinStatus, label: t('common.visited') },
	]);
</script>

<SegmentedControl bind:value {options} />
