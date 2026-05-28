<script lang="ts">
	import { t } from '$lib/i18n/index.svelte';
</script>

<div class="legal-doc">
	<h2>{t('legal.title')}</h2>
	<p class="meta">{t('legal.lastUpdated')}</p>

	<a class="nav-card" href="/legal/pdpo">{t('legal.pdpo')}</a>
	<a class="nav-card" href="/legal/gdpr">{t('legal.gdpr')}</a>
	<a class="nav-card" href="/legal/terms">{t('legal.terms')}</a>
	<a class="nav-card" href="/legal/community">{t('legal.community')}</a>
	<a class="nav-card" href="/legal/cookies">{t('legal.cookies')}</a>
	<a class="nav-card" href="/legal/contact">{t('legal.contact')}</a>
</div>
