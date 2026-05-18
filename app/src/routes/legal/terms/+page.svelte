<script lang="ts">
	import { i18n } from '$lib/i18n/index.svelte';
</script>

<div class="legal-doc">
	{#if i18n.locale === 'es'}
		<h2>Términos de Servicio</h2>
		<p class="meta">Última actualización: 18 de mayo de 2026 · Aplicable a los usuarios de Muse (lovemuse.app).</p>

		<p>Estos Términos de Servicio (los "Términos") regulan tu acceso y uso de la aplicación, sitio web y servicios relacionados de Muse (en conjunto, el "Servicio"). Al crear una cuenta, descargar la app móvil o usar el Servicio, aceptás quedar obligado por estos Términos.</p>

		<h3>1. Elegibilidad</h3>
		<p>Debés tener al menos 13 años. Si tenés menos de 18, necesitás el consentimiento de un padre, madre o tutor legal. Al usar el Servicio confirmás que cumplís estos requisitos y que tenés capacidad legal para contratar bajo las leyes de Hong Kong, incluyendo la <strong>Electronic Transactions Ordinance (Cap. 553)</strong>, que reconoce la aceptación electrónica como legalmente válida.</p>

		<h3>2. Tu cuenta</h3>
		<ul>
			<li>Brindá información veraz al registrarte y mantenela actualizada.</li>
			<li>Sos responsable de proteger tu contraseña y de todo lo que ocurra bajo tu cuenta.</li>
			<li>Notificanos inmediatamente a <a href="mailto:info@lovemuse.app">info@lovemuse.app</a> si sospechás un acceso no autorizado.</li>
		</ul>

		<h3>3. Uso aceptable</h3>
		<p>Te comprometés a no:</p>
		<ul>
			<li>violar ninguna ley aplicable, incluyendo las leyes de Hong Kong sobre difamación, obscenidad (Control of Obscene and Indecent Articles Ordinance, Cap. 390), propiedad intelectual o acceso no autorizado a sistemas informáticos (Cap. 200, arts. 27A y 161);</li>
			<li>subir o compartir contenido ilegal, difamatorio, hostigante, obsceno, amenazante o invasivo de la privacidad ajena;</li>
			<li>suplantar a una persona o entidad;</li>
			<li>hacer spam, scraping, ingeniería inversa o evadir limitaciones técnicas del Servicio;</li>
			<li>enviar mensajes comerciales electrónicos no solicitados (Unsolicited Electronic Messages Ordinance, Cap. 593).</li>
		</ul>

		<h3>4. Contenido del usuario</h3>
		<p>Conservás la titularidad del contenido que publicás (pins, calificaciones, comentarios, fotos, listas compartidas). Al publicar, nos otorgás una licencia mundial, no exclusiva y libre de regalías para alojar, almacenar, reproducir, modificar (solo para formatear) y distribuir ese contenido únicamente para operar, promocionar y mejorar el Servicio. La licencia termina al eliminar el contenido, salvo copias residuales en backups (purgadas en ciclos rotativos de 90 días) y contenido que otros ya hayan guardado o compartido.</p>
		<p>Declarás que tenés todos los derechos necesarios para publicar el contenido.</p>

		<h3>5. Datos de restaurantes</h3>
		<p>La información de restaurantes se agrega desde fuentes de terceros (Google Maps Platform, OpenStreetMap y similares) y aportes de usuarios. No garantizamos exactitud, completitud ni disponibilidad. Verificá los datos críticos (horarios, dietas, precios) directamente con el establecimiento.</p>

		<h3>6. Tarifas</h3>
		<p>Actualmente el Servicio es gratuito. Si introducimos funciones pagas, te avisaremos con anticipación y solo se cobrará si optás por usarlas.</p>

		<h3>7. Terminación</h3>
		<p>Podés eliminar tu cuenta cuando quieras. Podemos suspender o terminar tu acceso si infringís estos Términos, si tu uso plantea un riesgo de seguridad o legal, o si la ley nos lo exige. Cuando sea razonable, te daremos aviso previo. Las secciones que por su naturaleza deban sobrevivir a la terminación seguirán vigentes.</p>

		<h3>8. Descargo de responsabilidad</h3>
		<p>El Servicio se proporciona "tal cual" y "según disponibilidad", sin garantía alguna. En la máxima medida permitida por la ley de Hong Kong, rechazamos todas las garantías implícitas. Nada excluye o limita una responsabilidad que no pueda excluirse bajo la ley de Hong Kong (por ejemplo, fraude, o muerte o daño personal por negligencia bajo la Control of Exemption Clauses Ordinance, Cap. 71).</p>

		<h3>9. Limitación de responsabilidad</h3>
		<p>En la máxima medida permitida por la ley de Hong Kong, nuestra responsabilidad total no excederá el mayor de (a) el monto pagado en los doce (12) meses previos al hecho, o (b) HK$1.000. No somos responsables por daños indirectos, incidentales, especiales, consecuenciales o punitivos.</p>

		<h3>10. Indemnidad</h3>
		<p>Indemnizás y mantenés indemne a Muse, sus operadores y proveedores frente a cualquier reclamo de terceros derivado de (a) tu contenido, (b) tu uso del Servicio, o (c) tu incumplimiento de estos Términos o de la ley aplicable.</p>

		<h3>11. Cambios</h3>
		<p>Podemos actualizar estos Términos periódicamente. Los cambios materiales se notificarán con al menos 14 días de anticipación. Si no aceptás los nuevos Términos, dejá de usar el Servicio antes de la fecha efectiva.</p>

		<h3>12. Ley aplicable y jurisdicción</h3>
		<p>Estos Términos se rigen por las leyes de la Región Administrativa Especial de Hong Kong. Cualquier disputa se someterá a la jurisdicción exclusiva de los tribunales de Hong Kong. Nada limita los derechos de consumidor bajo la <strong>Trade Descriptions Ordinance (Cap. 362)</strong> u otras leyes imperativas de tu lugar de residencia habitual.</p>

		<h3>13. Contacto</h3>
		<p>Consultas sobre estos Términos: <a href="mailto:info@lovemuse.app">info@lovemuse.app</a>.</p>

	{:else if i18n.locale === 'it'}
		<h2>Termini di Servizio</h2>
		<p class="meta">Ultimo aggiornamento: 18 maggio 2026 · Validi per gli utenti di Muse (lovemuse.app).</p>

		<p>I presenti Termini di Servizio (i "Termini") disciplinano l'accesso e l'uso dell'applicazione Muse, del sito web e dei servizi correlati (collettivamente, il "Servizio"). Creando un account, scaricando l'app o usando il Servizio, accetti di essere vincolato da questi Termini.</p>

		<h3>1. Idoneità</h3>
		<p>Devi avere almeno 13 anni. Se hai meno di 18, ti serve il consenso di un genitore o tutore. Usando il Servizio confermi di soddisfare questi requisiti e di avere capacità legale per contrarre ai sensi delle leggi di Hong Kong, inclusa la <strong>Electronic Transactions Ordinance (Cap. 553)</strong>, che riconosce l'accettazione elettronica come legalmente valida.</p>

		<h3>2. Il tuo account</h3>
		<ul>
			<li>Fornisci informazioni accurate alla registrazione e mantienile aggiornate.</li>
			<li>Sei responsabile della custodia della password e di tutto ciò che avviene sotto il tuo account.</li>
			<li>Avvisaci immediatamente a <a href="mailto:info@lovemuse.app">info@lovemuse.app</a> in caso di accesso non autorizzato.</li>
		</ul>

		<h3>3. Uso accettabile</h3>
		<p>Ti impegni a non:</p>
		<ul>
			<li>violare leggi applicabili, incluse le leggi di Hong Kong su diffamazione, oscenità (Cap. 390), proprietà intellettuale o accesso non autorizzato a sistemi (Cap. 200, artt. 27A e 161);</li>
			<li>caricare contenuti illeciti, diffamatori, molesti, osceni, minacciosi o invasivi della privacy;</li>
			<li>impersonare persone o entità;</li>
			<li>fare spam, scraping, reverse-engineering o aggirare le limitazioni tecniche;</li>
			<li>inviare messaggi commerciali elettronici non sollecitati (Cap. 593).</li>
		</ul>

		<h3>4. Contenuto degli utenti</h3>
		<p>Mantieni la proprietà dei contenuti pubblicati. Pubblicando, ci concedi una licenza mondiale, non esclusiva e gratuita per ospitare, archiviare, riprodurre, modificare (solo per la formattazione) e distribuire i contenuti unicamente per gestire, promuovere e migliorare il Servizio. La licenza termina con l'eliminazione, salvo copie nei backup (eliminate in cicli rotativi di 90 giorni) e contenuti già salvati o condivisi da altri.</p>
		<p>Dichiari di avere tutti i diritti necessari per pubblicare il contenuto.</p>

		<h3>5. Dati dei ristoranti</h3>
		<p>Le informazioni sui ristoranti sono aggregate da terze parti (Google Maps Platform, OpenStreetMap) e da contributi degli utenti. Non ne garantiamo accuratezza, completezza o disponibilità. Verifica sempre i dettagli critici direttamente con il locale.</p>

		<h3>6. Costi</h3>
		<p>Il Servizio è attualmente gratuito. In caso di funzioni a pagamento future, riceverai un preavviso e ti sarà addebitato solo se scegli di usarle.</p>

		<h3>7. Risoluzione</h3>
		<p>Puoi eliminare l'account in qualsiasi momento. Possiamo sospendere o terminare l'accesso in caso di violazione, rischio per la sicurezza o legale, o quando la legge lo richieda. Quando ragionevole, daremo preavviso. Le sezioni che per natura sopravvivono restano in vigore.</p>

		<h3>8. Esclusione di garanzie</h3>
		<p>Il Servizio è fornito "così com'è" e "come disponibile", senza garanzie. Nella misura massima consentita dalla legge di Hong Kong, decliniamo ogni garanzia implicita. Nulla esclude o limita responsabilità che non possano essere escluse (per esempio, frode, o morte/lesioni per negligenza ai sensi della Control of Exemption Clauses Ordinance, Cap. 71).</p>

		<h3>9. Limitazione di responsabilità</h3>
		<p>Nella misura massima consentita dalla legge di Hong Kong, la nostra responsabilità complessiva non supererà il maggiore tra (a) l'importo pagato nei dodici (12) mesi precedenti, o (b) HK$1.000. Non siamo responsabili per danni indiretti, incidentali, speciali, consequenziali o punitivi.</p>

		<h3>10. Indennizzo</h3>
		<p>Ti impegni a indennizzare Muse, i suoi operatori e fornitori da qualsiasi reclamo di terzi derivante da (a) i tuoi contenuti, (b) il tuo uso del Servizio o (c) la tua violazione di questi Termini o della legge.</p>

		<h3>11. Modifiche</h3>
		<p>Possiamo aggiornare questi Termini periodicamente. Le modifiche sostanziali saranno notificate con almeno 14 giorni di anticipo. Se non accetti, smetti di usare il Servizio prima della data effettiva.</p>

		<h3>12. Legge applicabile e giurisdizione</h3>
		<p>I presenti Termini sono regolati dalle leggi della Regione Amministrativa Speciale di Hong Kong. Qualsiasi controversia è soggetta alla giurisdizione esclusiva dei tribunali di Hong Kong. Nulla limita i diritti del consumatore ai sensi della <strong>Trade Descriptions Ordinance (Cap. 362)</strong> o di altre leggi imperative del tuo luogo di residenza abituale.</p>

		<h3>13. Contatto</h3>
		<p>Domande sui presenti Termini: <a href="mailto:info@lovemuse.app">info@lovemuse.app</a>.</p>

	{:else}
		<h2>Terms of Service</h2>
		<p class="meta">Last updated: 18 May 2026 · Effective for users of Muse (lovemuse.app).</p>

		<p>These Terms of Service (the "Terms") govern your access to and use of the Muse application, website and related services (collectively, the "Service"). By creating an account, downloading the mobile app or otherwise using the Service, you agree to be bound by these Terms.</p>

		<h3>1. Eligibility</h3>
		<p>You must be at least 13 years old to use the Service. If you are under 18 you must have the consent of a parent or legal guardian. By using the Service you confirm that you meet these requirements and that you are legally capable of entering into a binding contract under the laws of Hong Kong, including the <strong>Electronic Transactions Ordinance (Cap. 553)</strong>, which recognises electronic acceptance as legally valid.</p>

		<h3>2. Your account</h3>
		<ul>
			<li>You must provide accurate information when registering and keep it up to date.</li>
			<li>You are responsible for safeguarding your password and for everything that happens under your account.</li>
			<li>Notify us immediately at <a href="mailto:info@lovemuse.app">info@lovemuse.app</a> if you suspect unauthorised access.</li>
		</ul>

		<h3>3. Acceptable use</h3>
		<p>You agree not to:</p>
		<ul>
			<li>break any applicable law, including Hong Kong laws on defamation, obscenity (Control of Obscene and Indecent Articles Ordinance, Cap. 390), intellectual property, or unauthorised access to computers (Cap. 200, ss.27A & 161);</li>
			<li>upload or share content that is unlawful, defamatory, harassing, obscene, threatening, or invasive of another's privacy;</li>
			<li>impersonate any person or entity, or misrepresent your affiliation with any person or entity;</li>
			<li>spam, scrape, reverse-engineer, or circumvent any technical limitation of the Service;</li>
			<li>use the Service to send unsolicited commercial electronic messages in breach of the Unsolicited Electronic Messages Ordinance (Cap. 593).</li>
		</ul>

		<h3>4. User content</h3>
		<p>You retain ownership of the content you post. By posting content you grant us a worldwide, non-exclusive, royalty-free licence to host, store, reproduce, modify (only to format for display), and distribute that content solely to operate, promote and improve the Service. The licence ends when you delete the content, except for residual copies in backups (purged on a rolling 90-day cycle) and for content that other users have already saved or shared.</p>
		<p>You represent that you have all rights necessary to post the content and that it does not infringe any third-party rights.</p>

		<h3>5. Restaurant data</h3>
		<p>Restaurant information shown in the Service is aggregated from third-party sources (Google Maps Platform, OpenStreetMap and similar) and from user contributions. We make no warranty about its accuracy, completeness or availability. Always verify critical details (opening hours, dietary options, prices) with the venue directly.</p>

		<h3>6. Fees</h3>
		<p>The Service is currently free to use. If we introduce paid features in the future, we will give you clear advance notice and you will only be charged if you opt in.</p>

		<h3>7. Termination</h3>
		<p>You may delete your account at any time. We may suspend or terminate your access if you breach these Terms, if your use poses a security or legal risk, or if we are required to do so by law. We will, where reasonably possible, give you prior notice. Sections that by their nature should survive termination (including ownership, disclaimers, liability, indemnification and governing law) survive.</p>

		<h3>8. Disclaimer</h3>
		<p>The Service is provided "as is" and "as available", without warranty of any kind, whether express, implied or statutory. To the maximum extent permitted by Hong Kong law, we disclaim all implied warranties, including merchantability, fitness for a particular purpose, and non-infringement. Nothing in these Terms excludes or limits any liability that cannot be excluded or limited under Hong Kong law (for example, liability for fraud, or for death or personal injury caused by negligence under the Control of Exemption Clauses Ordinance, Cap. 71).</p>

		<h3>9. Limitation of liability</h3>
		<p>To the maximum extent permitted by Hong Kong law, our aggregate liability arising out of or in connection with the Service or these Terms will not exceed the greater of (a) the amount you paid us in the twelve (12) months preceding the event giving rise to the claim, or (b) HK$1,000. We are not liable for indirect, incidental, special, consequential or punitive damages, or for loss of profits, data, goodwill or other intangible losses.</p>

		<h3>10. Indemnity</h3>
		<p>You agree to indemnify and hold harmless Muse, its operators and its service providers from any third-party claim arising from (a) your content, (b) your use of the Service, or (c) your breach of these Terms or applicable law.</p>

		<h3>11. Changes</h3>
		<p>We may update these Terms from time to time. Material changes will be notified at least 14 days before they take effect. If you do not agree to the new Terms, you should stop using the Service before the effective date.</p>

		<h3>12. Governing law & dispute resolution</h3>
		<p>These Terms are governed by the laws of the Hong Kong Special Administrative Region of the People's Republic of China, without regard to conflict-of-laws rules. Any dispute arising from or in connection with these Terms is subject to the exclusive jurisdiction of the courts of Hong Kong. Nothing in this section limits any consumer right you may have under the <strong>Trade Descriptions Ordinance (Cap. 362)</strong> or other mandatory consumer protection laws of your place of habitual residence.</p>

		<h3>13. Contact</h3>
		<p>For questions about these Terms, contact us at <a href="mailto:info@lovemuse.app">info@lovemuse.app</a>.</p>
	{/if}
</div>
