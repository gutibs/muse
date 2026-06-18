<script lang="ts">
	import { i18n } from '$lib/i18n/index.svelte';
</script>

<div class="legal-doc">
	{#if i18n.locale === 'es'}
		<h2>Política de Cookies</h2>
		<p class="meta">Última actualización: 18 de mayo de 2026</p>

		<p>Esta Política de Cookies explica cómo Muse utiliza cookies y tecnologías de almacenamiento similares (en conjunto, "cookies") en lovemuse.app y dentro de las aplicaciones móviles. Complementa nuestra <a href="/legal/privacy">Política de Privacidad</a> y refleja las pautas de la PCPD sobre tecnologías de rastreo online bajo la <strong>Personal Data (Privacy) Ordinance (Cap. 486)</strong>.</p>

		<h3>1. ¿Qué es una cookie?</h3>
		<p>Una cookie es un pequeño archivo de texto almacenado en tu dispositivo al visitar un sitio web. También usamos tecnologías relacionadas como <em>localStorage</em>, <em>sessionStorage</em> y la API Preferences de Capacitor en mobile. Por simplicidad las llamamos "cookies".</p>

		<h3>2. Cookies que usamos</h3>
		<p>Usamos pocas cookies, todas dentro de las categorías "estrictamente necesarias" o "de preferencia". <strong>No</strong> usamos cookies publicitarias ni pixeles de rastreo cross-site.</p>

		<h3>2.1 Estrictamente necesarias</h3>
		<ul>
			<li><strong>Tokens de autenticación</strong> (JWT access y refresh) — te mantienen logueado.</li>
			<li><strong>Token CSRF</strong> — protege endpoints sensibles contra cross-site request forgery.</li>
		</ul>

		<h3>2.2 Preferencias</h3>
		<ul>
			<li><strong>Preferencia de idioma</strong> (<code>muse_locale</code>) — recuerda si elegiste inglés, español o italiano.</li>
			<li><strong>Estado de UI</strong> — último filtro usado en mapa y feed, tips de onboarding descartados.</li>
		</ul>

		<h3>2.3 Terceros</h3>
		<p>Integramos dos servicios de terceros que pueden setear sus propias cookies:</p>
		<ul>
			<li><strong>Google Maps Platform</strong> — al cargar mapas o autocompletes.</li>
			<li><strong>Servidores de tiles de OpenStreetMap</strong> — pueden setear cookies técnicas.</li>
		</ul>
		<p>No usamos Google Analytics, Facebook Pixel ni cookies similares de perfilamiento o publicidad.</p>

		<h3>3. Tus opciones</h3>
		<p>Podés borrar las cookies desde la configuración de tu navegador o, en mobile, limpiando los datos de la app. Deshabilitar las cookies de autenticación cierra tu sesión.</p>

		<h3>4. Do Not Track</h3>
		<p>Algunos navegadores envían una señal "Do Not Track". Como no hacemos rastreo conductual cross-site, no tiene efecto adicional en nuestro Servicio.</p>

		<h3>5. Cambios</h3>
		<p>Si agregamos cookies que cambien materialmente el uso de tus datos, actualizaremos esta Política y, cuando corresponda, te pediremos consentimiento expreso.</p>

		<h3>6. Contacto</h3>
		<p><a href="mailto:info@lovemuse.app">info@lovemuse.app</a></p>

	{:else if i18n.locale === 'it'}
		<h2>Informativa sui Cookie</h2>
		<p class="meta">Ultimo aggiornamento: 18 maggio 2026</p>

		<p>Questa Informativa spiega come Muse utilizza i cookie e tecnologie di archiviazione simili (collettivamente, "cookie") su lovemuse.app e nelle app mobili. Integra la nostra <a href="/legal/privacy">Informativa sulla Privacy</a> e riflette le indicazioni della PCPD sull'uso di tecnologie di tracciamento online ai sensi della <strong>Personal Data (Privacy) Ordinance (Cap. 486)</strong>.</p>

		<h3>1. Cos'è un cookie?</h3>
		<p>Un cookie è un piccolo file di testo memorizzato sul tuo dispositivo. Utilizziamo anche <em>localStorage</em>, <em>sessionStorage</em> e l'API Preferences di Capacitor su mobile. Per semplicità le chiamiamo "cookie".</p>

		<h3>2. I cookie che usiamo</h3>
		<p>Usiamo pochi cookie, tutti nelle categorie "strettamente necessari" o "di preferenza". <strong>Non</strong> usiamo cookie pubblicitari né pixel di tracciamento cross-site.</p>

		<h3>2.1 Strettamente necessari</h3>
		<ul>
			<li><strong>Token di autenticazione</strong> (JWT access e refresh) — ti mantengono autenticato.</li>
			<li><strong>Token CSRF</strong> — protegge gli endpoint sensibili.</li>
		</ul>

		<h3>2.2 Preferenze</h3>
		<ul>
			<li><strong>Preferenza di lingua</strong> (<code>muse_locale</code>) — ricorda la lingua scelta.</li>
			<li><strong>Stato della UI</strong> — ultimo filtro, suggerimenti di onboarding chiusi.</li>
		</ul>

		<h3>2.3 Terze parti</h3>
		<p>Integriamo due servizi di terze parti che possono impostare i propri cookie:</p>
		<ul>
			<li><strong>Google Maps Platform</strong> — al caricamento di mappe o autocomplete.</li>
			<li><strong>Server di tile OpenStreetMap</strong> — possono impostare cookie tecnici.</li>
		</ul>
		<p>Non usiamo Google Analytics, Facebook Pixel o cookie simili di profilazione/pubblicità.</p>

		<h3>3. Le tue scelte</h3>
		<p>Puoi eliminare i cookie dalle impostazioni del browser o, su mobile, cancellando i dati dell'app. Disabilitare i cookie di autenticazione ti farà uscire.</p>

		<h3>4. Do Not Track</h3>
		<p>Alcuni browser inviano un segnale "Do Not Track". Poiché non effettuiamo tracciamento comportamentale cross-site, non ha effetti aggiuntivi.</p>

		<h3>5. Modifiche</h3>
		<p>Se aggiungiamo cookie che cambiano sostanzialmente l'uso dei tuoi dati, aggiorneremo questa Informativa e, ove necessario, chiederemo il tuo consenso esplicito.</p>

		<h3>6. Contatto</h3>
		<p><a href="mailto:info@lovemuse.app">info@lovemuse.app</a></p>

	{:else}
		<h2>Cookie Policy</h2>
		<p class="meta">Last updated: 18 May 2026</p>

		<p>This Cookie Policy explains how Muse uses cookies and similar storage technologies (collectively, "cookies") on the lovemuse.app website and within the Muse mobile applications. It supplements our <a href="/legal/privacy">Privacy Policy</a> and reflects the guidance of the PCPD on the use of online tracking technologies under the <strong>Personal Data (Privacy) Ordinance (Cap. 486)</strong>.</p>

		<h3>1. What is a cookie?</h3>
		<p>A cookie is a small text file stored on your device when you visit a website. We also use related technologies such as <em>localStorage</em>, <em>sessionStorage</em> and the Capacitor Preferences API on mobile. For simplicity we refer to all of them as "cookies".</p>

		<h3>2. Cookies we use</h3>
		<p>We use a small number of cookies, all of which fall into the "strictly necessary" or "preference" categories. We do <strong>not</strong> use advertising cookies or cross-site tracking pixels.</p>

		<h3>2.1 Strictly necessary</h3>
		<ul>
			<li><strong>Authentication tokens</strong> (JWT access & refresh) — keep you logged in.</li>
			<li><strong>CSRF token</strong> — protects sensitive backend endpoints from cross-site request forgery.</li>
		</ul>

		<h3>2.2 Preferences</h3>
		<ul>
			<li><strong>Language preference</strong> (<code>muse_locale</code>) — remembers whether you chose English, Spanish or Italian.</li>
			<li><strong>UI state</strong> — last-used filter on the map and feed, list of dismissed onboarding hints.</li>
		</ul>

		<h3>2.3 Third-party</h3>
		<p>We integrate two third-party services that may set their own cookies when you actively use their features:</p>
		<ul>
			<li><strong>Google Maps Platform</strong> — when a map tile or autocomplete result is loaded.</li>
			<li><strong>OpenStreetMap tile servers</strong> — may set technical cookies.</li>
		</ul>
		<p>We do not use Google Analytics, Facebook Pixel, or any similar profiling/advertising cookies.</p>

		<h3>3. Your choices</h3>
		<p>You can delete cookies through your browser settings or, on mobile, by clearing app storage. Disabling the authentication cookies will log you out and prevent you from using the Service.</p>

		<h3>4. Do Not Track</h3>
		<p>Some browsers send a "Do Not Track" signal. Because we do not engage in cross-site behavioural tracking, this signal has no additional effect on our Service.</p>

		<h3>5. Changes</h3>
		<p>If we add cookies that materially change how your data is used, we will update this Policy and, where required, ask for your express consent.</p>

		<h3>6. Contact</h3>
		<p><a href="mailto:info@lovemuse.app">info@lovemuse.app</a></p>
	{/if}
</div>
