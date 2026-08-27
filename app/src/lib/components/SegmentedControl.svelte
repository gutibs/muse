<script lang="ts" generics="T extends string">
	/**
	 * Selector de una opción entre varias, mutuamente excluyentes.
	 *
	 * Existe porque el formulario del pin ya tenía dos controles con este
	 * mismo markup escrito a mano (`StatusToggle` y el picker de idioma) y el
	 * nivel de visibilidad era el tercero. Las opciones y sus etiquetas las
	 * pone quien lo usa: acá no hay ningún valor de dominio.
	 */
	let {
		value = $bindable(),
		options,
		label = '',
		onchange,
	}: {
		value: T;
		options: { value: T; label: string }[];
		label?: string;
		/** Sólo se llama cuando la opción tapeada no era la que ya estaba. */
		onchange?: (value: T) => void;
	} = $props();

	function select(option: T) {
		if (option === value) return;
		value = option;
		onchange?.(option);
	}
</script>

{#if label}
	<span class="mb-1.5 block text-sm font-medium text-ink">{label}</span>
{/if}
<div class="flex gap-2">
	{#each options as option (option.value)}
		<button
			type="button"
			aria-pressed={value === option.value}
			class="min-h-11 flex-1 rounded-chip px-4 py-2.5 text-sm font-medium transition-colors active:scale-[0.98] {value ===
			option.value
				? 'bg-jade text-white'
				: 'bg-cream-dark text-ink-muted'}"
			onclick={() => select(option.value)}
		>
			{option.label}
		</button>
	{/each}
</div>
