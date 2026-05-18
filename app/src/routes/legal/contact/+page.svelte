<script lang="ts">
	import { i18n } from '$lib/i18n/index.svelte';
</script>

<div class="legal-doc">
	{#if i18n.locale === 'es'}
		<h2>Contacto</h2>
		<p class="meta">Última actualización: 18 de mayo de 2026</p>

		<p>Somos un equipo chico. La forma más rápida de encontrarnos es por email.</p>

		<h3>Consultas generales, soporte y feedback</h3>
		<p><a href="mailto:info@lovemuse.app">info@lovemuse.app</a></p>

		<h3>Privacidad y protección de datos (PDPO)</h3>
		<p>
			Para Data Access Requests, Data Correction Requests, oposiciones y cualquier
			consulta sobre la <strong>Personal Data (Privacy) Ordinance (Cap. 486)</strong>:<br />
			<a href="mailto:info@lovemuse.app?subject=Privacy%20request">info@lovemuse.app</a>
			(asunto: "Privacy request")
		</p>
		<p>Respondemos las solicitudes bajo PDPO dentro de los 40 días.</p>

		<h3>Reportes de contenido y apelaciones</h3>
		<p>
			Para reportar contenido que viole las <a href="/legal/community">Normas de la Comunidad</a> o apelar una decisión de moderación:<br />
			<a href="mailto:info@lovemuse.app?subject=Content%20report">info@lovemuse.app</a>
			(asunto: "Content report" o "Appeal")
		</p>

		<h3>Notificaciones de copyright (estilo DMCA)</h3>
		<p>
			Si creés que un contenido infringe tu copyright, enviá una notificación con (a) identificación de la obra, (b) URL o captura del contenido infractor, (c) tus datos de contacto y (d) declaración de buena fe de que sos el titular:<br />
			<a href="mailto:info@lovemuse.app?subject=Copyright%20notice">info@lovemuse.app</a>
		</p>

		<h3>Requerimientos de las fuerzas de seguridad</h3>
		<p>
			Los requerimientos autorizados de autoridades de Hong Kong (PDPO, Crimes Ordinance, PDPO (Amendment) Ordinance 2021) deben enviarse a
			<a href="mailto:info@lovemuse.app?subject=Law%20enforcement">info@lovemuse.app</a>
			en papel membretado oficial que identifique a la autoridad, la base legal y el alcance.
		</p>

		<h3>Autoridad regulatoria</h3>
		<p>
			Office of the Privacy Commissioner for Personal Data, Hong Kong (PCPD)<br />
			12/F, Sunlight Tower, 248 Queen's Road East, Wanchai, Hong Kong<br />
			<a href="https://www.pcpd.org.hk" rel="noopener" target="_blank">www.pcpd.org.hk</a>
		</p>

	{:else if i18n.locale === 'it'}
		<h2>Contatto</h2>
		<p class="meta">Ultimo aggiornamento: 18 maggio 2026</p>

		<p>Siamo un piccolo team. Il modo più veloce per raggiungerci è via email.</p>

		<h3>Richieste generali, supporto e feedback</h3>
		<p><a href="mailto:info@lovemuse.app">info@lovemuse.app</a></p>

		<h3>Privacy e protezione dei dati (PDPO)</h3>
		<p>
			Per Data Access Requests, Data Correction Requests, opt-out e qualsiasi domanda sulla <strong>Personal Data (Privacy) Ordinance (Cap. 486)</strong>:<br />
			<a href="mailto:info@lovemuse.app?subject=Privacy%20request">info@lovemuse.app</a>
			(oggetto: "Privacy request")
		</p>
		<p>Rispondiamo entro 40 giorni come previsto dalla PDPO.</p>

		<h3>Segnalazioni di contenuti e ricorsi</h3>
		<p>
			Per segnalare contenuti che violano le <a href="/legal/community">Linee Guida</a> o per ricorrere contro una moderazione:<br />
			<a href="mailto:info@lovemuse.app?subject=Content%20report">info@lovemuse.app</a>
			(oggetto: "Content report" o "Appeal")
		</p>

		<h3>Notifiche di copyright (in stile DMCA)</h3>
		<p>
			Se ritieni che un contenuto violi il tuo copyright, inviaci notifica con (a) identificazione dell'opera, (b) URL o screenshot, (c) i tuoi contatti, (d) dichiarazione in buona fede di essere il titolare:<br />
			<a href="mailto:info@lovemuse.app?subject=Copyright%20notice">info@lovemuse.app</a>
		</p>

		<h3>Richieste delle forze dell'ordine</h3>
		<p>
			Le richieste autorizzate delle autorità di Hong Kong (PDPO, Crimes Ordinance, PDPO (Amendment) Ordinance 2021) vanno inviate a
			<a href="mailto:info@lovemuse.app?subject=Law%20enforcement">info@lovemuse.app</a>
			su carta intestata ufficiale.
		</p>

		<h3>Autorità di regolamentazione</h3>
		<p>
			Office of the Privacy Commissioner for Personal Data, Hong Kong (PCPD)<br />
			12/F, Sunlight Tower, 248 Queen's Road East, Wanchai, Hong Kong<br />
			<a href="https://www.pcpd.org.hk" rel="noopener" target="_blank">www.pcpd.org.hk</a>
		</p>

	{:else}
		<h2>Contact</h2>
		<p class="meta">Last updated: 18 May 2026</p>

		<p>We're a small team. The fastest way to reach us is by email.</p>

		<h3>General enquiries, support and feedback</h3>
		<p><a href="mailto:info@lovemuse.app">info@lovemuse.app</a></p>

		<h3>Privacy and data protection (PDPO)</h3>
		<p>
			For Data Access Requests, Data Correction Requests, opt-outs and any question relating to the
			<strong>Personal Data (Privacy) Ordinance (Cap. 486)</strong>:<br />
			<a href="mailto:info@lovemuse.app?subject=Privacy%20request">info@lovemuse.app</a>
			(subject line: "Privacy request")
		</p>
		<p>We respond to PDPO requests within 40 days, as required by the Ordinance.</p>

		<h3>Content reports and appeals</h3>
		<p>
			To report content that breaks our <a href="/legal/community">Community Guidelines</a> or to appeal a moderation decision:<br />
			<a href="mailto:info@lovemuse.app?subject=Content%20report">info@lovemuse.app</a>
			(subject line: "Content report" or "Appeal")
		</p>

		<h3>Copyright (DMCA-style) notices</h3>
		<p>
			If you believe content on Muse infringes your copyright, send us a notice including (a) identification of the work, (b) the URL or screenshot of the allegedly infringing content, (c) your contact details, and (d) a good faith statement that you are the rights holder or an authorised agent:<br />
			<a href="mailto:info@lovemuse.app?subject=Copyright%20notice">info@lovemuse.app</a>
		</p>

		<h3>Law-enforcement requests</h3>
		<p>
			Authorised requests from Hong Kong authorities (e.g. under the PDPO, the Crimes Ordinance or the Personal Data (Privacy) (Amendment) Ordinance 2021) should be sent to
			<a href="mailto:info@lovemuse.app?subject=Law%20enforcement">info@lovemuse.app</a>.
			We require service on official letterhead identifying the authority, the legal basis, and a specific scope.
		</p>

		<h3>Regulatory authority</h3>
		<p>
			Office of the Privacy Commissioner for Personal Data, Hong Kong (PCPD)<br />
			12/F, Sunlight Tower, 248 Queen's Road East, Wanchai, Hong Kong<br />
			<a href="https://www.pcpd.org.hk" rel="noopener" target="_blank">www.pcpd.org.hk</a>
		</p>
	{/if}
</div>
