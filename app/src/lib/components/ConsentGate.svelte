<script lang="ts">
	/**
	 * Frena a las cuentas que nunca dejaron constancia de haber aceptado nada.
	 *
	 * `ConsentRecord` llegó con una migración schema-only y sin backfill, así
	 * que las cuentas anteriores no tienen ninguna fila: en producción, 16 de
	 * 17. Bajo GDPR la carga de la prueba es del responsable, y para esas no
	 * hay con qué demostrar qué aceptaron ni cuándo.
	 *
	 * No se puede cerrar tocando afuera, a diferencia del resto de los modales
	 * del proyecto: aceptar es la única salida y un cierre accidental dejaría
	 * la cuenta usando la app sin haber aceptado nada, que es justo el estado
	 * que esto viene a terminar. Qué se acepta lo decide el backend
	 * (`pendingPolicies`), no el cliente.
	 */
	import { t } from '$lib/i18n/index.svelte';
	import { legalUrl } from '$lib/legal';
	import { authStore } from '$lib/stores/auth.store.svelte';
	import { logSilent } from '$lib/utils/logger';

	let saving = $state(false);
	let error = $state('');

	async function aceptar() {
		saving = true;
		error = '';
		try {
			await authStore.acceptPolicies();
		} catch (err) {
			logSilent('consentGate:accept', err);
			error = t('consent.gateError');
		} finally {
			saving = false;
		}
	}
</script>

<!-- Safe areas propias: como `UpdateGate`, esto se dibuja por encima de
	AppShell, así que no hereda las suyas. Sin esto los botones caen dentro de
	la franja del indicador de inicio y no se pueden tocar. -->
<div
	class="fixed inset-0 z-50 flex items-end justify-center bg-black/40 sm:items-center"
	style="padding-bottom: var(--sab); padding-left: var(--sal); padding-right: var(--sar);"
>
	<div class="w-full max-w-sm rounded-t-card bg-white p-6 shadow-elevated sm:rounded-card">
		<h2 class="font-serif text-xl font-semibold text-ink">{t('consent.gateTitle')}</h2>
		<p class="mt-3 text-sm text-ink-light">{t('consent.gateBody')}</p>

		<div class="mt-4 flex flex-col gap-2">
			<a
				href={legalUrl('privacy')}
				target="_blank"
				rel="noopener noreferrer"
				class="min-h-11 text-sm text-jade underline active:opacity-70"
			>
				{t('consent.privacyLink')}
			</a>
			<a
				href={legalUrl('terms')}
				target="_blank"
				rel="noopener noreferrer"
				class="min-h-11 text-sm text-jade underline active:opacity-70"
			>
				{t('consent.termsLink')}
			</a>
		</div>

		{#if error}
			<div
				data-testid="consent-gate-error"
				class="mt-3 rounded-button bg-blush-light/20 px-4 py-3 text-sm text-blush"
			>
				{error}
			</div>
		{/if}

		<button
			type="button"
			data-testid="consent-gate-accept"
			disabled={saving}
			onclick={aceptar}
			class="mt-6 min-h-11 w-full rounded-button bg-jade px-4 text-base font-medium text-white active:scale-95 disabled:opacity-60"
		>
			{t('consent.gateAccept')}
		</button>

		<!-- La salida. Sin esto el único camino es aceptar, y si el POST falla
			siempre —un 500, un token en mal estado— la cuenta queda encerrada
			con un botón que no funciona y ninguna forma de salir. Cerrar sesión
			también es la respuesta honesta a quien no quiere aceptar. -->
		<button
			type="button"
			data-testid="consent-gate-logout"
			disabled={saving}
			onclick={() => authStore.logout()}
			class="mt-2 min-h-11 w-full rounded-button px-4 text-sm text-ink-light active:opacity-70 disabled:opacity-60"
		>
			{t('consent.gateLogout')}
		</button>
	</div>
</div>
