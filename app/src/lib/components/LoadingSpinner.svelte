<script lang="ts">
	let { size = 24 }: { size?: number } = $props();
</script>

<svg
	class="animate-spin text-jade"
	width={size}
	height={size}
	viewBox="0 0 24 24"
	fill="none"
>
	<circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="3" opacity="0.2" />
	<path
		d="M12 2a10 10 0 0 1 10 10"
		stroke="currentColor"
		stroke-width="3"
		stroke-linecap="round"
	/>
</svg>
