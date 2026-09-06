<script lang="ts">
	/**
	 * Campo de contraseña con el ojito de ver/ocultar.
	 *
	 * Único lugar donde vive ese SVG. Estaba pegado tres veces (login y los dos
	 * del registro) y faltaba en los otros cinco campos de contraseña de la app:
	 * el de la contraseña nueva del reset y los cuatro de Ajustes. Probando el
	 * APK V1.3.0 el 2026-09-06, elegir una contraseña nueva sin poder verla fue
	 * justo el paso que salió mal. Es el mismo patrón que dejó el corazón de
	 * rating copiado en 17 archivos: si vas a agregar un sexto campo, usá esto.
	 */
	import { t } from '$lib/i18n/index.svelte';

	interface Props {
		value: string;
		id: string;
		/** `current-password` para verificar identidad, `new-password` al elegir una. */
		autocomplete?: 'current-password' | 'new-password';
		placeholder?: string;
		required?: boolean;
		name?: string;
		minlength?: number;
		/** Color del foco. El borrado de cuenta usa `focus:border-blush`. */
		class?: string;
	}

	let {
		value = $bindable(),
		id,
		autocomplete = 'current-password',
		placeholder = '',
		required = false,
		name = undefined,
		minlength = undefined,
		class: className = 'focus:border-jade'
	}: Props = $props();

	let visible = $state(false);
</script>

<div class="relative">
	<input
		{id}
		{name}
		{required}
		{autocomplete}
		{placeholder}
		{minlength}
		type={visible ? 'text' : 'password'}
		bind:value
		class="w-full rounded-input border border-cream-dark bg-white px-4 py-3 pr-12 text-base text-ink outline-none transition-colors {className}"
	/>
	<!-- min-h-11/min-w-11: los 44px del HIG que pide el proyecto. Los tres
	     campos que ya tenían ojito no llegaban — el del registro era un ícono
	     de 20px con p-1, o sea 28px de área tocable. -->
	<button
		type="button"
		onclick={() => (visible = !visible)}
		aria-label={visible ? t('login.hidePassword') : t('login.showPassword')}
		class="absolute right-1 top-1/2 flex min-h-11 min-w-11 -translate-y-1/2 items-center justify-center rounded-lg text-ink-muted active:scale-90"
	>
		{#if visible}
			<svg class="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
				<path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"/>
				<line x1="1" y1="1" x2="23" y2="23"/>
			</svg>
		{:else}
			<svg class="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
				<path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/>
			</svg>
		{/if}
	</button>
</div>
