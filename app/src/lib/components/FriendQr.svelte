<script lang="ts">
	import QRCode from 'qrcode';
	import { t } from '$lib/i18n/index.svelte';
	import { friendCodePayload, rotateFriendCode } from '$lib/services/friend-code.service';
	import { logSilent } from '$lib/utils/logger';

	let { code }: { code: string } = $props();

	// El código rotado pisa a la prop sin copiarla a `$state`: copiar y
	// sincronizar con un `$effect` termina en `effect_update_depth_exceeded`
	// (la lección de F2.D). Con `$derived`, el servidor sigue siendo la fuente
	// y esto es sólo el override local hasta que el perfil se recargue.
	let rotado = $state<string | null>(null);
	let rotando = $state(false);
	let error = $state('');
	let svg = $state('');

	const actual = $derived(rotado ?? code);

	$effect(() => {
		const payload = friendCodePayload(actual);
		QRCode.toString(payload, {
			type: 'svg',
			errorCorrectionLevel: 'M',
			margin: 1,
			color: { dark: '#000000', light: '#ffffff' }
		})
			.then((generado) => {
				svg = generado;
			})
			.catch((err) => {
				logSilent('FriendQr.generar', err);
				error = t('friendCode.qrFailed');
			});
	});

	async function rotar() {
		if (rotando) return;
		rotando = true;
		error = '';
		try {
			rotado = await rotateFriendCode();
		} catch (err) {
			logSilent('FriendQr.rotar', err);
			error = t('friendCode.rotateFailed');
		} finally {
			rotando = false;
		}
	}
</script>

<div class="flex flex-col items-center gap-4">
	<p class="text-center text-sm text-ink-muted">{t('friendCode.explain')}</p>

	<div class="w-56 max-w-full rounded-2xl bg-white p-3 shadow-sm">
		<!-- eslint-disable-next-line svelte/no-at-html-tags -- lo genera qrcode, no entra texto de nadie -->
		{@html svg}
	</div>

	{#if error}
		<p class="text-center text-sm text-red-600">{error}</p>
	{/if}

	<button
		type="button"
		data-testid="rotar-codigo"
		onclick={rotar}
		disabled={rotando}
		class="min-h-11 px-4 text-sm text-ink-muted underline active:opacity-80 disabled:opacity-50"
	>
		{rotando ? t('friendCode.rotating') : t('friendCode.rotate')}
	</button>
</div>
