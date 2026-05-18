<script lang="ts">
	import { i18n } from '$lib/i18n/index.svelte';
</script>

<div class="legal-doc">
	{#if i18n.locale === 'es'}
		<h2>Normas de la Comunidad</h2>
		<p class="meta">Última actualización: 18 de mayo de 2026</p>

		<p>Muse es un espacio para descubrir y compartir restaurantes con la gente en la que confiás. Lo que hace que valga la pena abrir el feed son los aportes honestos, amables y útiles. Estas Normas explican qué esperamos de quienes usan el Servicio y qué hará que se elimine contenido o cuentas.</p>

		<h3>1. Sé honesto</h3>
		<ul>
			<li>Calificá solo restaurantes en los que efectivamente comiste.</li>
			<li>No aceptes pagos ni regalías a cambio de una calificación positiva.</li>
			<li>No publiques reseñas falsas en contra de competidores ni a favor propio.</li>
		</ul>

		<h3>2. Sé respetuoso</h3>
		<ul>
			<li>Nada de hostigamiento, amenazas, discursos de odio o ataques por raza, etnia, origen nacional, religión, discapacidad, género, identidad de género, orientación sexual, edad o cualquier otra característica protegida.</li>
			<li>Criticá la comida, no al personal. Exponer y "escrachar" a trabajadores individuales no está permitido.</li>
		</ul>

		<h3>3. Cumplí la ley</h3>
		<p>No publiques contenido que viole la ley, incluyendo las leyes de Hong Kong sobre difamación, obscenidad (Cap. 390), incitación, infracción de propiedad intelectual o mensajes comerciales no solicitados (Cap. 593). El doxxing — publicar datos privados de personas identificables — está prohibido y puede infringir también la Personal Data (Privacy) Ordinance (Cap. 486).</p>

		<h3>4. Respetá la privacidad</h3>
		<ul>
			<li>No publiques fotos de personas identificables sin su consentimiento.</li>
			<li>No compartas datos personales de terceros (teléfonos, direcciones, documentos, datos financieros).</li>
			<li>Tratá la actividad compartida por amigos como privada de esa amistad: no la republiques en otro lado sin permiso.</li>
		</ul>

		<h3>5. Nada de spam ni estafas</h3>
		<ul>
			<li>Nada de promoción masiva, spam de afiliados ni mensajes no solicitados repetidos.</li>
			<li>Nada de phishing, links falsos, malware ni suplantación del equipo de Muse.</li>
		</ul>

		<h3>6. Contenido adulto y seguridad</h3>
		<p>El contenido pornográfico o sexualmente explícito, la violencia gratuita y el contenido que sexualiza a menores están prohibidos y serán reportados a las autoridades. El contenido que promueve autolesiones o suicidio no está permitido; si estás en crisis, contactá a Samaritans Hong Kong al 2896&nbsp;0000.</p>

		<h3>7. Propiedad intelectual</h3>
		<p>Publicá solo fotos y textos que tengas derecho a compartir. Si creés que se vulneró tu copyright, escribí a <a href="mailto:info@lovemuse.app">info@lovemuse.app</a> con la URL o captura, la identificación de la obra y una declaración de que sos el titular.</p>

		<h3>8. Reportes y aplicación</h3>
		<p>Si ves contenido que viole estas Normas, reportalo escribiendo a <a href="mailto:info@lovemuse.app">info@lovemuse.app</a>. Revisaremos el reporte. Según gravedad e historial podemos: eliminar el contenido; advertir al usuario; suspender o terminar la cuenta; denunciar el caso ante las fuerzas de seguridad cuando la ley lo exija.</p>

		<h3>9. Apelaciones</h3>
		<p>Si creés que se actuó sobre tu contenido o cuenta por error, respondé al email de notificación dentro de los 30 días. Revisaremos la apelación y te responderemos.</p>

	{:else if i18n.locale === 'it'}
		<h2>Linee Guida della Comunità</h2>
		<p class="meta">Ultimo aggiornamento: 18 maggio 2026</p>

		<p>Muse è un luogo per scoprire e condividere ristoranti con le persone di cui ti fidi. Sono i contributi onesti, gentili e utili a rendere il feed degno di essere aperto. Queste Linee Guida indicano cosa ci aspettiamo da chi utilizza il Servizio e cosa porterà alla rimozione di contenuti o account.</p>

		<h3>1. Sii onesto</h3>
		<ul>
			<li>Valuta solo i ristoranti che hai effettivamente visitato.</li>
			<li>Non accettare pagamenti o omaggi in cambio di una valutazione positiva.</li>
			<li>Non pubblicare recensioni false contro un concorrente o a favore proprio.</li>
		</ul>

		<h3>2. Sii rispettoso</h3>
		<ul>
			<li>Nessuna molestia, minaccia, discorso d'odio o attacco basato su razza, etnia, origine nazionale, religione, disabilità, genere, identità di genere, orientamento sessuale, età o altra caratteristica protetta.</li>
			<li>Critica il cibo, non il personale. Non è ammesso esporre o screditare singoli lavoratori.</li>
		</ul>

		<h3>3. Rispetta la legge</h3>
		<p>Non pubblicare contenuti che violino la legge, comprese le leggi di Hong Kong su diffamazione, oscenità (Cap. 390), istigazione, violazione della proprietà intellettuale o messaggi commerciali non sollecitati (Cap. 593). Il doxxing — pubblicare dati di contatto privati di persone identificabili — è vietato e può violare anche la Personal Data (Privacy) Ordinance (Cap. 486).</p>

		<h3>4. Rispetta la privacy</h3>
		<ul>
			<li>Non pubblicare foto di persone identificabili senza il loro consenso.</li>
			<li>Non condividere dati personali di terzi (numeri di telefono, indirizzi, documenti, informazioni finanziarie).</li>
			<li>Tratta l'attività condivisa dagli amici come privata: non ripubblicarla altrove senza permesso.</li>
		</ul>

		<h3>5. Niente spam, niente truffe</h3>
		<ul>
			<li>Nessuna promozione di massa, spam di affiliazione o messaggi non sollecitati ripetuti.</li>
			<li>Nessun phishing, link falsi, malware o impersonazione dello staff di Muse.</li>
		</ul>

		<h3>6. Contenuti per adulti e sicurezza</h3>
		<p>I contenuti pornografici o sessualmente espliciti, la violenza gratuita e i contenuti che sessualizzano i minori sono vietati e saranno segnalati alle autorità competenti. I contenuti che promuovono autolesionismo o suicidio non sono ammessi; se sei in difficoltà, contatta i Samaritans Hong Kong al 2896&nbsp;0000.</p>

		<h3>7. Proprietà intellettuale</h3>
		<p>Pubblica solo foto e testi che hai diritto di condividere. Se ritieni che il tuo copyright sia stato violato, scrivi a <a href="mailto:info@lovemuse.app">info@lovemuse.app</a> indicando l'URL o lo screenshot, l'identificazione dell'opera e una dichiarazione di essere il titolare dei diritti.</p>

		<h3>8. Segnalazioni e applicazione</h3>
		<p>Se vedi contenuti che violano queste Linee Guida, segnalali scrivendo a <a href="mailto:info@lovemuse.app">info@lovemuse.app</a>. Esamineremo la segnalazione. A seconda della gravità e della storia possiamo: rimuovere il contenuto; avvisare l'utente; sospendere o terminare l'account; segnalare il caso alle autorità quando richiesto dalla legge.</p>

		<h3>9. Ricorsi</h3>
		<p>Se ritieni che il tuo contenuto o account sia stato gestito per errore, rispondi all'email di notifica entro 30 giorni. Esamineremo il ricorso e ti risponderemo.</p>

	{:else}
		<h2>Community Guidelines</h2>
		<p class="meta">Last updated: 18 May 2026</p>

		<p>Muse is a place to discover and share restaurants with the people you trust. Honest, kind and useful contributions are what make the feed worth opening. These Guidelines tell you what we expect from everyone using the Service and what will get content or accounts removed.</p>

		<h3>1. Be honest</h3>
		<ul>
			<li>Only rate restaurants you have actually visited.</li>
			<li>Don't accept payment or freebies in exchange for a positive rating.</li>
			<li>Don't post fake reviews for a competitor's venue or for your own.</li>
		</ul>

		<h3>2. Be respectful</h3>
		<ul>
			<li>No harassment, threats, hate speech, or attacks on the basis of race, ethnicity, national origin, religion, disability, gender, gender identity, sexual orientation, age or any other protected characteristic.</li>
			<li>Criticise the food, not the staff. Naming and shaming individual workers is not allowed.</li>
		</ul>

		<h3>3. Keep it legal</h3>
		<p>Do not post content that breaks the law, including Hong Kong laws on defamation, obscenity (Cap. 390), incitement, intellectual property infringement, or unsolicited commercial messages (Cap. 593). Doxxing — publishing private contact details of identifiable individuals — is prohibited and may also breach the Personal Data (Privacy) Ordinance (Cap. 486).</p>

		<h3>4. Respect privacy</h3>
		<ul>
			<li>Don't post photos of identifiable people without their consent.</li>
			<li>Don't share personal data (phone numbers, home addresses, ID numbers, financial information) of other people.</li>
			<li>Treat friends' shared activity as private to that friendship: don't republish it elsewhere without permission.</li>
		</ul>

		<h3>5. No spam, no scams</h3>
		<ul>
			<li>No bulk promotion, affiliate spam, or repeated unsolicited messages.</li>
			<li>No phishing, fake links, malware, or impersonation of Muse staff.</li>
		</ul>

		<h3>6. Adult content & safety</h3>
		<p>Pornographic or sexually explicit content, gratuitous violence, and content that sexualises minors are prohibited and will be reported to the relevant authorities. Content that promotes self-harm or suicide is not permitted; if you are in distress, please contact the Samaritans Hong Kong on 2896&nbsp;0000.</p>

		<h3>7. Intellectual property</h3>
		<p>Only post photos and text you have the right to share. If you believe your copyright has been infringed, email <a href="mailto:info@lovemuse.app">info@lovemuse.app</a> with the URL or screenshot, identification of the work and a statement that you are the rights holder.</p>

		<h3>8. Reporting and enforcement</h3>
		<p>If you see content that violates these Guidelines, report it by emailing <a href="mailto:info@lovemuse.app">info@lovemuse.app</a>. We will review the report. Depending on severity and history, we may remove the content; warn the user; suspend or terminate the account; or report the matter to law enforcement when legally required.</p>

		<h3>9. Appeals</h3>
		<p>If you believe your content or account was actioned in error, reply to the notification email within 30 days. We will review the appeal and respond.</p>
	{/if}
</div>
