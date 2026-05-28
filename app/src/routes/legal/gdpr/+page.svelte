<script lang="ts">
	import { i18n } from '$lib/i18n/index.svelte';
</script>

<div class="legal-doc">
	{#if i18n.locale === 'es'}
		<h2>Política de Privacidad GDPR</h2>
		<p class="meta">Última actualización: 28 de mayo de 2026 · Aplicable a usuarios de Muse en la UE, EEE y Reino Unido.</p>

		<p>Esta Política explica cómo Muse ("nosotros") trata los datos personales de usuarios en la Unión Europea ("UE"), el Espacio Económico Europeo ("EEE") y el Reino Unido ("RU"), en cumplimiento del <strong>Reglamento (UE) 2016/679</strong> ("GDPR") y, cuando corresponda, del <strong>UK GDPR</strong> y la Data Protection Act 2018. Si residís fuera de estas jurisdicciones, se aplica nuestra <a href="/legal/pdpo">Política de Privacidad PDPO</a>.</p>

		<h3>1. Quiénes somos (Responsable, art. 4.7 GDPR)</h3>
		<p>Muse opera como un servicio en línea disponible en lovemuse.app y mediante aplicaciones móviles. A los efectos del GDPR actuamos como <em>responsable del tratamiento</em> respecto de los datos personales que recopilamos de vos. No hemos designado un Delegado de Protección de Datos porque nuestras actividades principales no lo requieren conforme al art. 37 GDPR, pero podés contactarnos en <a href="mailto:info@lovemuse.app">info@lovemuse.app</a>.</p>

		<h3>2. Datos personales que recopilamos</h3>
		<p>Solo recopilamos los datos necesarios para prestar el servicio:</p>
		<ul>
			<li><strong>Datos de cuenta:</strong> dirección de email, nombre visible, contraseña (almacenada con hash), preferencia de idioma.</li>
			<li><strong>Datos de perfil (opcionales):</strong> biografía, ciudad, preferencias dietarias, cocina favorita, usuario de Instagram, sitio web, teléfono, avatar.</li>
			<li><strong>Contenido que generás:</strong> restaurantes que marcás como "visitado" o "para visitar", calificaciones, comentarios, listas compartidas.</li>
			<li><strong>Grafo social:</strong> conexiones de amistad e invitaciones que enviás o aceptás.</li>
			<li><strong>Datos técnicos del dispositivo:</strong> IP, tipo de dispositivo, sistema operativo, versión de la app, logs de fallos, ubicación aproximada o precisa <em>solo</em> cuando otorgás el permiso explícito.</li>
			<li><strong>Comunicaciones:</strong> emails que nos enviás a <a href="mailto:info@lovemuse.app">info@lovemuse.app</a>.</li>
		</ul>
		<p>No tratamos categorías especiales de datos (art. 9 GDPR). No recopilamos conscientemente datos de menores de 16 años (art. 8 GDPR); algunos Estados miembros admiten el consentimiento desde los 13 — cuando aplique en tu país, se observa la edad menor.</p>

		<h3>3. Finalidades y base jurídica (art. 6 GDPR)</h3>
		<ul>
			<li><strong>Ejecución de un contrato (art. 6.1.b):</strong> crear y mantener tu cuenta, permitirte fijar/calificar/compartir restaurantes, mostrar la actividad de amigos, enviar emails transaccionales.</li>
			<li><strong>Interés legítimo (art. 6.1.f):</strong> seguridad del servicio, prevención de abusos, mejora del producto. Podés oponerte conforme al art. 21.</li>
			<li><strong>Obligación legal (art. 6.1.c):</strong> conservación y divulgación de datos cuando lo exija el derecho de la UE o de un Estado miembro.</li>
			<li><strong>Consentimiento (art. 6.1.a):</strong> tratamiento de tu ubicación precisa cuando otorgás el permiso del dispositivo. Podés retirarlo en cualquier momento (art. 7.3).</li>
		</ul>

		<h3>4. Con quién compartimos los datos</h3>
		<p><strong>No</strong> vendemos tus datos personales ni hacemos perfilado publicitario. Compartimos solo:</p>
		<ul>
			<li><strong>Con otros usuarios:</strong> nombre, avatar, ciudad, pins, calificaciones y listas son visibles para amigos; las listas con link público quedan accesibles a quien tenga el link.</li>
			<li><strong>Con encargados (art. 28 GDPR):</strong> hosting (AWS, EC2/RDS en EE.UU.), email transaccional (Resend), mapas y lugares (Google Maps Platform, OpenStreetMap/Nominatim vía nuestro proxy). Cada encargado está vinculado por contrato conforme al art. 28.3.</li>
			<li><strong>Por motivos legales:</strong> orden judicial, requerimiento legítimo o defensa de nuestros derechos.</li>
		</ul>

		<h3>5. Transferencias internacionales (Capítulo V GDPR)</h3>
		<p>Cuando transferimos datos fuera del EEE/RU (en particular a EE.UU.), nos apoyamos en las <strong>Cláusulas Contractuales Tipo</strong> (Decisión de Ejecución 2021/914) o el <strong>UK Addendum</strong>, junto a medidas suplementarias (TLS, controles de acceso, minimización). Copia de las SCC a pedido.</p>

		<h3>6. Conservación (art. 5.1.e)</h3>
		<p>Conservamos los datos solo durante el tiempo necesario. Al eliminar tu cuenta, borramos o anonimizamos en 30 días, salvo obligación legal. Backups con copias residuales se purgan en ciclo rotativo de 90 días.</p>

		<h3>7. Seguridad (art. 32)</h3>
		<p>Aplicamos medidas técnicas y organizativas apropiadas al riesgo: TLS 1.2+, contraseñas con hash (PBKDF2), controles de acceso, rate-limiting, logging. En caso de violación con riesgo para tus derechos, notificaremos a la autoridad de control en 72 hs (art. 33) y a los usuarios afectados cuando el riesgo sea alto (art. 34).</p>

		<h3>8. Exactitud (art. 5.1.d)</h3>
		<p>Podés editar la mayoría de tus datos desde el perfil. Si algo es inexacto, corregilo o escribinos.</p>

		<h3>9. Tus derechos (art. 15–22 GDPR)</h3>
		<ul>
			<li><strong>Acceso (art. 15)</strong> — confirmación y copia de los datos.</li>
			<li><strong>Rectificación (art. 16)</strong> — corrección de datos inexactos.</li>
			<li><strong>Supresión (art. 17)</strong> — "derecho al olvido", con las excepciones del art. 17.3.</li>
			<li><strong>Limitación (art. 18)</strong> — restringir el tratamiento en ciertos casos.</li>
			<li><strong>Portabilidad (art. 20)</strong> — recibir tus datos en formato estructurado y transmitirlos a otro responsable.</li>
			<li><strong>Oposición (art. 21)</strong> — al tratamiento basado en interés legítimo.</li>
			<li><strong>Retirar consentimiento (art. 7.3)</strong> — en cualquier momento, sin efecto retroactivo.</li>
			<li><strong>No ser objeto de decisiones automatizadas (art. 22)</strong> — no las usamos.</li>
		</ul>
		<p>Para ejercer estos derechos, escribinos a <a href="mailto:info@lovemuse.app">info@lovemuse.app</a> desde la dirección asociada a tu cuenta. Respondemos en un mes (prorrogable dos meses si la solicitud es compleja, art. 12.3). Gratuito salvo solicitud manifiestamente infundada o excesiva (art. 12.5).</p>

		<h3>10. Reclamación ante autoridad de control (art. 77)</h3>
		<p>Tenés derecho a presentar una reclamación ante la autoridad de control de tu residencia habitual, lugar de trabajo o lugar de la presunta infracción. Directorio UE: <a href="https://edpb.europa.eu/about-edpb/about-edpb/members_en" rel="noopener" target="_blank">edpb.europa.eu</a>. Para el RU: <a href="https://ico.org.uk" rel="noopener" target="_blank">ico.org.uk</a>.</p>

		<h3>11. Cambios</h3>
		<p>Podemos actualizar esta Política. Los cambios materiales se notifican en la app o por email con al menos 14 días de antelación.</p>

		<h3>12. Contacto</h3>
		<p>Consultas y ejercicio de derechos: <a href="mailto:info@lovemuse.app">info@lovemuse.app</a>.</p>

	{:else if i18n.locale === 'it'}
		<h2>Informativa sulla Privacy GDPR</h2>
		<p class="meta">Ultimo aggiornamento: 28 maggio 2026 · Valida per gli utenti di Muse nell'UE, SEE e Regno Unito.</p>

		<p>Questa Informativa spiega come Muse ("noi") tratta i dati personali degli utenti nell'Unione Europea ("UE"), nello Spazio Economico Europeo ("SEE") e nel Regno Unito ("UK"), in conformità al <strong>Regolamento (UE) 2016/679</strong> ("GDPR") e, ove applicabile, al <strong>UK GDPR</strong> e al Data Protection Act 2018. Se risiedi al di fuori di queste giurisdizioni, si applica la nostra <a href="/legal/pdpo">Informativa sulla Privacy PDPO</a>.</p>

		<h3>1. Chi siamo (Titolare, art. 4(7) GDPR)</h3>
		<p>Muse opera come servizio online su lovemuse.app e tramite app mobili. Ai fini del GDPR agiamo come <em>titolare del trattamento</em>. Non abbiamo nominato un Responsabile della Protezione dei Dati perché le nostre attività principali non lo richiedono (art. 37 GDPR). Contatto privacy: <a href="mailto:info@lovemuse.app">info@lovemuse.app</a>.</p>

		<h3>2. Dati personali che raccogliamo</h3>
		<p>Raccogliamo solo i dati necessari per il servizio:</p>
		<ul>
			<li><strong>Dati dell'account:</strong> email, nome visualizzato, password (con hash), preferenza di lingua.</li>
			<li><strong>Dati del profilo (facoltativi):</strong> biografia, città, preferenze alimentari, cucina preferita, Instagram, sito web, telefono, avatar.</li>
			<li><strong>Contenuti creati:</strong> ristoranti "visitato"/"da visitare", valutazioni, commenti, liste condivise.</li>
			<li><strong>Grafo sociale:</strong> connessioni di amicizia e inviti.</li>
			<li><strong>Dati tecnici:</strong> IP, dispositivo, OS, versione app, log di crash, posizione <em>solo</em> con permesso esplicito.</li>
			<li><strong>Comunicazioni:</strong> email inviate a <a href="mailto:info@lovemuse.app">info@lovemuse.app</a>.</li>
		</ul>
		<p>Non trattiamo categorie particolari di dati (art. 9 GDPR). Non raccogliamo consapevolmente dati di persone sotto i 16 anni (art. 8 GDPR); alcuni Stati membri consentono il consenso dai 13 anni — ove applicabile, si osserva l'età inferiore.</p>

		<h3>3. Finalità e base giuridica (art. 6 GDPR)</h3>
		<ul>
			<li><strong>Esecuzione di un contratto (art. 6, par. 1, lett. b):</strong> account, pin/valutazioni/condivisioni, feed amici, email transazionali.</li>
			<li><strong>Legittimo interesse (art. 6, par. 1, lett. f):</strong> sicurezza, prevenzione abusi, miglioramento del prodotto. Puoi opporti ai sensi dell'art. 21.</li>
			<li><strong>Obbligo legale (art. 6, par. 1, lett. c):</strong> conservazione/divulgazione ove richiesto dal diritto UE o di uno Stato membro.</li>
			<li><strong>Consenso (art. 6, par. 1, lett. a):</strong> posizione precisa, se concedi il permesso del dispositivo. Revoca in qualsiasi momento (art. 7, par. 3).</li>
		</ul>

		<h3>4. Come condividiamo i dati</h3>
		<p><strong>Non</strong> vendiamo i tuoi dati né facciamo profilazione pubblicitaria. Condividiamo solo:</p>
		<ul>
			<li><strong>Con altri utenti:</strong> nome, avatar, città, pin, valutazioni e liste visibili agli amici; le liste con link pubblico sono accessibili a chi ha il link.</li>
			<li><strong>Con responsabili del trattamento (art. 28 GDPR):</strong> hosting (AWS, EC2/RDS USA), email (Resend), mappe e luoghi (Google Maps Platform, OpenStreetMap/Nominatim tramite proxy). Ogni responsabile vincolato da contratto conforme all'art. 28, par. 3.</li>
			<li><strong>Per motivi legali:</strong> ordini, richieste legittime, difesa dei nostri diritti.</li>
		</ul>

		<h3>5. Trasferimenti internazionali (Capo V GDPR)</h3>
		<p>Quando trasferiamo dati fuori dal SEE/UK (in particolare negli USA), facciamo affidamento sulle <strong>Clausole Contrattuali Tipo</strong> (Decisione 2021/914) o sull'<strong>UK Addendum</strong>, con misure supplementari (TLS, controlli di accesso, minimizzazione). Copia delle SCC su richiesta.</p>

		<h3>6. Conservazione (art. 5, par. 1, lett. e)</h3>
		<p>Conserviamo i dati solo per il tempo necessario. Eliminando l'account, cancelliamo o anonimizziamo entro 30 giorni, salvo obblighi legali. I backup sono purgati in un ciclo rotativo di 90 giorni.</p>

		<h3>7. Sicurezza (art. 32)</h3>
		<p>Applichiamo misure adeguate al rischio: TLS 1.2+, password con hash (PBKDF2), controlli di accesso, rate-limiting, logging. In caso di violazione con rischio per i tuoi diritti, notifichiamo l'autorità entro 72 ore (art. 33) e gli utenti interessati se il rischio è elevato (art. 34).</p>

		<h3>8. Esattezza (art. 5, par. 1, lett. d)</h3>
		<p>Puoi modificare la maggior parte dei dati dalla schermata profilo. Se qualcosa non è accurato, correggilo o scrivici.</p>

		<h3>9. I tuoi diritti (art. 15–22 GDPR)</h3>
		<ul>
			<li><strong>Accesso (art. 15)</strong> — conferma e copia dei dati.</li>
			<li><strong>Rettifica (art. 16)</strong> — correzione di dati inesatti.</li>
			<li><strong>Cancellazione (art. 17)</strong> — "diritto all'oblio", salve le eccezioni dell'art. 17, par. 3.</li>
			<li><strong>Limitazione (art. 18)</strong> — restrizione del trattamento in determinati casi.</li>
			<li><strong>Portabilità (art. 20)</strong> — ricevere i dati in formato strutturato e trasmetterli ad altri.</li>
			<li><strong>Opposizione (art. 21)</strong> — al trattamento basato sul legittimo interesse.</li>
			<li><strong>Revoca del consenso (art. 7, par. 3)</strong> — in qualsiasi momento, senza effetto retroattivo.</li>
			<li><strong>Non essere soggetto a decisioni automatizzate (art. 22)</strong> — non le utilizziamo.</li>
		</ul>
		<p>Per esercitare questi diritti, scrivi a <a href="mailto:info@lovemuse.app">info@lovemuse.app</a> dall'indirizzo associato al tuo account. Rispondiamo entro un mese (prorogabile di due mesi per richieste complesse, art. 12, par. 3). Gratuito salvo richieste manifestamente infondate o eccessive (art. 12, par. 5).</p>

		<h3>10. Reclamo all'autorità di controllo (art. 77)</h3>
		<p>Puoi proporre reclamo all'autorità di controllo del tuo Stato membro. Per l'Italia: <a href="https://www.garanteprivacy.it" rel="noopener" target="_blank">Garante per la Protezione dei Dati Personali</a>. Elenco UE: <a href="https://edpb.europa.eu/about-edpb/about-edpb/members_en" rel="noopener" target="_blank">edpb.europa.eu</a>.</p>

		<h3>11. Modifiche</h3>
		<p>Possiamo aggiornare l'Informativa. Le modifiche sostanziali saranno notificate in app o via email almeno 14 giorni prima.</p>

		<h3>12. Contatto</h3>
		<p>Domande o esercizio dei diritti: <a href="mailto:info@lovemuse.app">info@lovemuse.app</a>.</p>

	{:else}
		<h2>GDPR Privacy Policy</h2>
		<p class="meta">Last updated: 28 May 2026 · Effective for users of Muse in the EU, EEA and the United Kingdom.</p>

		<p>This Policy explains how Muse ("we", "us", "our") processes personal data of users in the European Union ("EU"), the European Economic Area ("EEA") and the United Kingdom ("UK"), in compliance with <strong>Regulation (EU) 2016/679</strong> ("GDPR") and, where applicable, the <strong>UK GDPR</strong> and the UK Data Protection Act 2018. If you reside outside these jurisdictions, our <a href="/legal/pdpo">PDPO Privacy Policy</a> applies instead.</p>

		<h3>1. Who we are (Controller, art. 4(7) GDPR)</h3>
		<p>Muse operates as an online service available at lovemuse.app and via mobile applications. For the purposes of the GDPR we act as the <em>data controller</em>. We have not appointed a Data Protection Officer because our core activities do not require one (art. 37 GDPR). Privacy contact: <a href="mailto:info@lovemuse.app">info@lovemuse.app</a>.</p>

		<h3>2. Personal data we collect</h3>
		<p>We collect only the data we need to run the service:</p>
		<ul>
			<li><strong>Account data:</strong> email, display name, password (hashed), language preference.</li>
			<li><strong>Profile data (optional):</strong> bio, city, dietary preferences, favourite cuisine, Instagram handle, website, phone, avatar.</li>
			<li><strong>Content you create:</strong> restaurants pinned as "visited" or "to visit", ratings, comments, shared lists.</li>
			<li><strong>Social graph:</strong> friend connections and invitations.</li>
			<li><strong>Device & technical data:</strong> IP, device, OS, app version, crash logs, location <em>only</em> with explicit permission.</li>
			<li><strong>Communications:</strong> emails sent to <a href="mailto:info@lovemuse.app">info@lovemuse.app</a>.</li>
		</ul>
		<p>We do not process special categories of data (art. 9 GDPR). We do not knowingly collect data from individuals under 16 (art. 8 GDPR); some member states permit consent from age 13 — where this applies in your country, the lower age is observed.</p>

		<h3>3. Purposes and legal basis (art. 6 GDPR)</h3>
		<ul>
			<li><strong>Performance of a contract (art. 6(1)(b)):</strong> account, pinning/rating/sharing, friends' feed, transactional emails.</li>
			<li><strong>Legitimate interests (art. 6(1)(f)):</strong> security, abuse prevention, product improvement. You may object under art. 21.</li>
			<li><strong>Legal obligation (art. 6(1)(c)):</strong> retention/disclosure where required by EU or member-state law.</li>
			<li><strong>Consent (art. 6(1)(a)):</strong> precise location, when you grant the device permission. Withdrawable at any time (art. 7(3)).</li>
		</ul>

		<h3>4. How we share data</h3>
		<p>We do <strong>not</strong> sell your personal data and we do not run advertising-based profiling. We share only:</p>
		<ul>
			<li><strong>With other users:</strong> display name, avatar, city, pins, ratings and shared lists are visible to friends; public-link lists are accessible to anyone with the link.</li>
			<li><strong>With processors (art. 28 GDPR):</strong> hosting (AWS, EC2/RDS in the US), transactional email (Resend), mapping & places (Google Maps Platform, OpenStreetMap/Nominatim via our backend proxy). Each processor is bound by a written agreement meeting art. 28(3).</li>
			<li><strong>For legal reasons:</strong> court orders, lawful requests, or to defend our rights.</li>
		</ul>

		<h3>5. International transfers (Chapter V GDPR)</h3>
		<p>Where we transfer data outside the EEA/UK (in particular to the United States), we rely on the European Commission's <strong>Standard Contractual Clauses</strong> (Decision 2021/914) or the <strong>UK Addendum</strong>, together with supplementary measures (TLS encryption, access controls, data minimisation). A copy of the relevant SCCs is available on request.</p>

		<h3>6. Retention (art. 5(1)(e))</h3>
		<p>We keep personal data only for as long as is necessary. On account deletion, we delete or anonymise within 30 days, except where retention is required to comply with a legal obligation. Backups are purged on a rolling 90-day cycle.</p>

		<h3>7. Security (art. 32)</h3>
		<p>We apply technical and organisational measures appropriate to the risk: TLS 1.2+, hashed password storage (PBKDF2), access controls, rate-limiting and logging. If we become aware of a personal data breach likely to result in a risk to your rights and freedoms, we will notify the supervisory authority within 72 hours where feasible (art. 33) and affected users without undue delay where the risk is high (art. 34).</p>

		<h3>8. Accuracy (art. 5(1)(d))</h3>
		<p>You can edit most of your personal data directly from your profile screen. If any data is inaccurate, please correct it in-app or write to us.</p>

		<h3>9. Your rights (art. 15–22 GDPR)</h3>
		<ul>
			<li><strong>Access (art. 15)</strong> — confirmation and a copy of your data.</li>
			<li><strong>Rectification (art. 16)</strong> — correction of inaccurate data.</li>
			<li><strong>Erasure (art. 17)</strong> — "right to be forgotten", subject to art. 17(3) exceptions.</li>
			<li><strong>Restriction (art. 18)</strong> — limit processing in certain cases.</li>
			<li><strong>Portability (art. 20)</strong> — receive your data in a structured format and transmit it.</li>
			<li><strong>Objection (art. 21)</strong> — to processing based on legitimate interests.</li>
			<li><strong>Withdraw consent (art. 7(3))</strong> — at any time, without retroactive effect.</li>
			<li><strong>Not be subject to automated decision-making (art. 22)</strong> — we do not use any.</li>
		</ul>
		<p>To exercise any of these rights, email <a href="mailto:info@lovemuse.app">info@lovemuse.app</a> from the address linked to your account. We respond within one month (extendable by two further months for complex requests, art. 12(3)). Free of charge unless the request is manifestly unfounded or excessive (art. 12(5)).</p>

		<h3>10. Right to lodge a complaint (art. 77)</h3>
		<p>You have the right to lodge a complaint with the supervisory authority of your habitual residence, place of work or where the alleged infringement took place. Directory: <a href="https://edpb.europa.eu/about-edpb/about-edpb/members_en" rel="noopener" target="_blank">edpb.europa.eu</a>. For the UK: <a href="https://ico.org.uk" rel="noopener" target="_blank">ico.org.uk</a>.</p>

		<h3>11. Changes</h3>
		<p>We may update this Policy. Material changes will be notified in-app or by email at least 14 days before they take effect.</p>

		<h3>12. Contact</h3>
		<p>Questions or rights requests: <a href="mailto:info@lovemuse.app">info@lovemuse.app</a>.</p>
	{/if}
</div>
