<script lang="ts">
	let {
		message,
		type = 'info',
		visible = false,
	}: {
		message: string;
		type?: 'info' | 'success' | 'error';
		visible: boolean;
	} = $props();

	const colors = {
		info: 'bg-ink text-white',
		success: 'bg-jade text-white',
		error: 'bg-blush text-white',
	};
</script>

{#if visible}
	<div
		class="fixed bottom-20 left-1/2 z-50 -translate-x-1/2 rounded-card px-5 py-3 shadow-elevated {colors[type]}"
		role="alert"
	>
		<p class="text-sm font-medium">{message}</p>
	</div>
{/if}
