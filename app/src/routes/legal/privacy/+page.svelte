<script lang="ts">
	import { i18n } from '$lib/i18n/index.svelte';
</script>

<div class="legal-doc">
	{#if i18n.locale === 'es'}
		<h2>Política de Privacidad</h2>
		<p class="meta">Última actualización: 28 de mayo de 2026 · Aplicable a todos los usuarios de Muse (lovemuse.app).</p>

		<p>Esta Política de Privacidad cubre el tratamiento de datos personales de todos los usuarios de Muse, con independencia de tu lugar de residencia. Se divide en dos partes: la <strong>Parte A (GDPR)</strong> aplica a usuarios en la Unión Europea, el EEE y el Reino Unido; la <strong>Parte B (PDPO)</strong> aplica a usuarios en Hong Kong y demás jurisdicciones. Al crear una cuenta aceptás esta Política en su conjunto.</p>

		<h2>Parte A — GDPR (UE, EEE y Reino Unido)</h2>
		<p>Esta parte explica cómo Muse ("nosotros") trata los datos personales de usuarios en la Unión Europea ("UE"), el Espacio Económico Europeo ("EEE") y el Reino Unido ("RU"), en cumplimiento del <strong>Reglamento (UE) 2016/679</strong> ("GDPR") y, cuando corresponda, del <strong>UK GDPR</strong> y la Data Protection Act 2018.</p>

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

		<h2>Parte B — PDPO (Hong Kong)</h2>
		<p>Esta parte está redactada para cumplir con la <strong>Personal Data (Privacy) Ordinance (Cap. 486)</strong> de Hong Kong ("PDPO") y los seis Principios de Protección de Datos ("DPP") emitidos por la Office of the Privacy Commissioner for Personal Data, Hong Kong ("PCPD").</p>

		<h3>1. Quiénes somos (Data User)</h3>
		<p>Muse opera como un servicio en línea disponible en lovemuse.app y mediante aplicaciones móviles. A los efectos de la PDPO, actuamos como <em>Data User</em> respecto de los datos personales que recopilamos de vos. Los datos de contacto para consultas de privacidad figuran al final de esta Política.</p>

		<h3>2. Datos personales que recopilamos</h3>
		<p>Recopilamos los mismos datos descritos en la Parte A (datos de cuenta, perfil, contenido, grafo social, datos técnicos y comunicaciones), solo en la medida necesaria para prestar el servicio.</p>
		<p>No recopilamos datos de menores de 13 años de forma consciente. Si creés que un menor nos proporcionó datos personales, contactanos y los eliminaremos.</p>

		<h3>3. Finalidades (DPP 1 y 3)</h3>
		<p>Tratamos tus datos personales con los siguientes fines:</p>
		<ul>
			<li>Crear, mantener y proteger tu cuenta.</li>
			<li>Permitirte fijar, calificar y compartir restaurantes con tus amigos.</li>
			<li>Mostrarte la actividad de tus amigos en un feed personalizado.</li>
			<li>Enviar emails transaccionales (invitaciones, recuperación de contraseña, alertas de seguridad).</li>
			<li>Mejorar el servicio, depurar fallos y prevenir abusos.</li>
			<li>Cumplir con las leyes aplicables y con requerimientos legítimos de autoridades.</li>
		</ul>
		<p>No usaremos tus datos con una finalidad sustancialmente distinta sin tu consentimiento expreso y voluntario previo, conforme al DPP 3.</p>

		<h3>4. Con quién compartimos los datos (DPP 3)</h3>
		<p><strong>No</strong> vendemos tus datos personales. Solo los compartimos en estos casos:</p>
		<ul>
			<li><strong>Con otros usuarios:</strong> tu nombre, avatar, ciudad, pins, calificaciones y listas compartidas son visibles para tus amigos; las listas que compartas por link público quedan accesibles a quien tenga ese link.</li>
			<li><strong>Con proveedores de servicio (Data Processors):</strong> hosting (AWS, EC2/RDS en Estados Unidos), email transaccional (Resend), mapas y datos de lugares (Google Maps Platform, OpenStreetMap/Nominatim vía nuestro proxy backend). Procesan datos por instrucción nuestra bajo salvaguardas contractuales.</li>
			<li><strong>Por motivos legales:</strong> cuando lo exija una orden judicial, citación u otro requerimiento legítimo, incluidos los de autoridades de Hong Kong bajo la PDPO u otras Ordenanzas.</li>
		</ul>

		<h3>5. Transferencias internacionales</h3>
		<p>Aunque la Sección 33 de la PDPO aún no está vigente, aplicamos su espíritu de forma voluntaria. Cuando transferimos datos fuera de Hong Kong (por ejemplo, a AWS en EE.UU. o Resend en UE/EE.UU.) garantizamos que el destinatario esté obligado por contrato a proteger los datos con un estándar equivalente al de la PDPO, que la transferencia se realice con cifrado TLS y que se limite a lo necesario.</p>

		<h3>6. Retención (DPP 2)</h3>
		<p>Conservamos los datos personales solo durante el tiempo necesario. Cuando eliminás tu cuenta, borramos o anonimizamos tus datos en 30 días, salvo cuando la retención sea requerida para cumplir una obligación legal, resolver disputas o hacer cumplir nuestros acuerdos. Las copias en backups se purgan en un ciclo rotativo de 90 días.</p>

		<h3>7. Seguridad (DPP 4)</h3>
		<p>Aplicamos medidas razonables y prácticas: TLS 1.2+ para todo el tráfico, contraseñas con hash (PBKDF2 de Django), controles de acceso, rate-limiting en endpoints sensibles y logging. Si detectamos una violación con riesgo real de daño significativo, notificaremos a los usuarios afectados y, cuando corresponda, a la PCPD sin demora indebida.</p>

		<h3>8. Exactitud (DPP 2)</h3>
		<p>Podés editar la mayoría de tus datos personales desde la pantalla de perfil. Si algo es inexacto, corregilo ahí mismo o escribinos.</p>

		<h3>9. Tus derechos (DPP 5 y 6)</h3>
		<p>Bajo la PDPO tenés derecho a estar informado de nuestras prácticas (DPP 5); verificar si tenemos tus datos y pedir copia (Data Access Request, art. 18); pedir corrección de datos inexactos (Data Correction Request, art. 22); y oponerte a marketing directo (hoy no enviamos marketing directo).</p>
		<p>Para ejercer estos derechos, escribinos a <a href="mailto:info@lovemuse.app">info@lovemuse.app</a> desde la dirección asociada a tu cuenta. Respondemos en 40 días, conforme la PDPO. Podemos cobrar una tarifa razonable por un Data Access Request, en línea con las pautas de la PCPD.</p>

		<h3>10. Reclamos</h3>
		<p>Si considerás que no cumplimos con la PDPO, podés presentar un reclamo ante la PCPD: 12/F, Sunlight Tower, 248 Queen's Road East, Wanchai, Hong Kong — <a href="https://www.pcpd.org.hk" rel="noopener" target="_blank">www.pcpd.org.hk</a>.</p>

		<h3>Cambios y contacto</h3>
		<p>Podemos actualizar esta Política. Los cambios materiales se notifican en la app o por email con al menos 14 días de antelación. Consultas y ejercicio de derechos: <a href="mailto:info@lovemuse.app">info@lovemuse.app</a>.</p>

	{:else if i18n.locale === 'it'}
		<h2>Informativa sulla Privacy</h2>
		<p class="meta">Ultimo aggiornamento: 28 maggio 2026 · Valida per tutti gli utenti di Muse (lovemuse.app).</p>

		<p>Questa Informativa sulla Privacy disciplina il trattamento dei dati personali di tutti gli utenti di Muse, indipendentemente dal luogo di residenza. È divisa in due parti: la <strong>Parte A (GDPR)</strong> si applica agli utenti nell'Unione Europea, nel SEE e nel Regno Unito; la <strong>Parte B (PDPO)</strong> si applica agli utenti di Hong Kong e delle altre giurisdizioni. Creando un account accetti questa Informativa nel suo complesso.</p>

		<h2>Parte A — GDPR (UE, SEE e Regno Unito)</h2>
		<p>Questa parte spiega come Muse ("noi") tratta i dati personali degli utenti nell'Unione Europea ("UE"), nello Spazio Economico Europeo ("SEE") e nel Regno Unito ("UK"), in conformità al <strong>Regolamento (UE) 2016/679</strong> ("GDPR") e, ove applicabile, al <strong>UK GDPR</strong> e al Data Protection Act 2018.</p>

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

		<h2>Parte B — PDPO (Hong Kong)</h2>
		<p>Questa parte è redatta in conformità alla <strong>Personal Data (Privacy) Ordinance (Cap. 486)</strong> di Hong Kong ("PDPO") e ai sei Data Protection Principles ("DPP") emanati dall'Office of the Privacy Commissioner for Personal Data, Hong Kong ("PCPD").</p>

		<h3>1. Chi siamo (Data User)</h3>
		<p>Muse opera come servizio online disponibile su lovemuse.app e tramite applicazioni mobili. Ai fini della PDPO, agiamo come <em>Data User</em> rispetto ai dati personali che raccogliamo. I contatti per richieste sulla privacy sono in fondo a questa Informativa.</p>

		<h3>2. Dati personali che raccogliamo</h3>
		<p>Raccogliamo gli stessi dati descritti nella Parte A (dati dell'account, profilo, contenuti, grafo sociale, dati tecnici e comunicazioni), solo nella misura necessaria a fornire il servizio.</p>
		<p>Non raccogliamo consapevolmente dati di minori di 13 anni. Se ritieni che un minore ci abbia fornito dati, contattaci e li elimineremo.</p>

		<h3>3. Finalità (DPP 1 e 3)</h3>
		<p>Trattiamo i tuoi dati personali per: creare, mantenere e proteggere il tuo account; permetterti di salvare, valutare e condividere ristoranti con gli amici; mostrarti l'attività dei tuoi amici in un feed; inviare email transazionali; migliorare il servizio; rispettare la legge e le richieste legittime delle autorità.</p>
		<p>Non li useremo per finalità materialmente diverse senza il tuo consenso esplicito e volontario, come richiesto dal DPP 3.</p>

		<h3>4. Con chi condividiamo i dati (DPP 3)</h3>
		<p><strong>Non</strong> vendiamo i tuoi dati personali. Li condividiamo solo:</p>
		<ul>
			<li><strong>Con altri utenti:</strong> nome, avatar, città, pin, valutazioni e liste condivise sono visibili agli amici; le liste pubbliche sono accessibili a chi ha il link.</li>
			<li><strong>Con fornitori di servizio (Data Processors):</strong> hosting (AWS, EC2/RDS USA), email (Resend), mappe (Google Maps Platform, OpenStreetMap/Nominatim via proxy backend). Operano su nostre istruzioni con garanzie contrattuali.</li>
			<li><strong>Per motivi legali:</strong> ordini del tribunale o richieste legittime, anche delle autorità di Hong Kong.</li>
		</ul>

		<h3>5. Trasferimenti internazionali</h3>
		<p>Sebbene la Sezione 33 della PDPO non sia ancora in vigore, ne applichiamo lo spirito volontariamente: il destinatario è vincolato contrattualmente a proteggere i dati con uno standard equivalente, la trasmissione avviene con TLS e si limita a quanto necessario.</p>

		<h3>6. Conservazione (DPP 2)</h3>
		<p>Conserviamo i dati solo per il tempo necessario. Eliminando l'account, cancelliamo o anonimizziamo entro 30 giorni, salvo obblighi legali. I backup sono purgati in un ciclo rotativo di 90 giorni.</p>

		<h3>7. Sicurezza (DPP 4)</h3>
		<p>Applichiamo TLS 1.2+, password con hash (PBKDF2 di Django), controlli di accesso, rate-limiting e logging. In caso di violazione con rischio reale di danno significativo, notificheremo utenti e, se opportuno, la PCPD senza indebito ritardo.</p>

		<h3>8. Accuratezza (DPP 2)</h3>
		<p>Puoi modificare la maggior parte dei dati dalla schermata profilo. Se qualcosa è inesatto, correggilo o scrivici.</p>

		<h3>9. I tuoi diritti (DPP 5 e 6)</h3>
		<p>Ai sensi della PDPO hai diritto a essere informato delle nostre prassi, verificare se conserviamo i tuoi dati e richiederne copia (Data Access Request, art. 18), richiederne la correzione (Data Correction Request, art. 22) e opporti a marketing diretto.</p>
		<p>Per esercitarli, scrivi a <a href="mailto:info@lovemuse.app">info@lovemuse.app</a> dall'indirizzo collegato al tuo account. Rispondiamo entro 40 giorni. Possiamo richiedere una tariffa ragionevole per un Data Access Request, in linea con le indicazioni della PCPD.</p>

		<h3>10. Reclami</h3>
		<p>Se ritieni che non abbiamo rispettato la PDPO, puoi presentare reclamo alla PCPD: 12/F, Sunlight Tower, 248 Queen's Road East, Wanchai, Hong Kong — <a href="https://www.pcpd.org.hk" rel="noopener" target="_blank">www.pcpd.org.hk</a>.</p>

		<h3>Modifiche e contatto</h3>
		<p>Possiamo aggiornare questa Informativa. Le modifiche sostanziali saranno notificate in app o via email almeno 14 giorni prima. Domande o esercizio dei diritti: <a href="mailto:info@lovemuse.app">info@lovemuse.app</a>.</p>

	{:else}
		<h2>Privacy Policy</h2>
		<p class="meta">Last updated: 28 May 2026 · Effective for all users of Muse (lovemuse.app).</p>

		<p>This Privacy Policy governs the processing of personal data of all Muse users, regardless of where you live. It is split into two parts: <strong>Part A (GDPR)</strong> applies to users in the European Union, the EEA and the United Kingdom; <strong>Part B (PDPO)</strong> applies to users in Hong Kong and other jurisdictions. By creating an account you accept this Policy as a whole.</p>

		<h2>Part A — GDPR (EU, EEA and United Kingdom)</h2>
		<p>This part explains how Muse ("we", "us", "our") processes personal data of users in the European Union ("EU"), the European Economic Area ("EEA") and the United Kingdom ("UK"), in compliance with <strong>Regulation (EU) 2016/679</strong> ("GDPR") and, where applicable, the <strong>UK GDPR</strong> and the UK Data Protection Act 2018.</p>

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

		<h2>Part B — PDPO (Hong Kong)</h2>
		<p>This part is written to comply with the <strong>Personal Data (Privacy) Ordinance (Cap. 486)</strong> of Hong Kong ("PDPO") and the six Data Protection Principles ("DPPs") issued by the Office of the Privacy Commissioner for Personal Data, Hong Kong ("PCPD").</p>

		<h3>1. Who we are (Data User)</h3>
		<p>Muse is operated as an online service available at lovemuse.app and via mobile applications. For the purposes of the PDPO, we act as the <em>Data User</em> in respect of the personal data we collect from you. Contact details for privacy enquiries are set out at the end of this Policy.</p>

		<h3>2. Personal data we collect</h3>
		<p>We collect the same data described in Part A (account, profile, content, social graph, device and communications data), only to the extent needed to run the service.</p>
		<p>We do not knowingly collect data from individuals under the age of 13. If you believe a minor has provided us with personal data, contact us and we will delete it.</p>

		<h3>3. Purposes of collection (DPP 1 & 3)</h3>
		<p>We collect and use your personal data for the following purposes:</p>
		<ul>
			<li>Creating, maintaining and securing your account.</li>
			<li>Letting you pin, rate and share restaurants with friends.</li>
			<li>Showing you your friends' activity in a personalised feed.</li>
			<li>Sending transactional emails (invitations, password resets, security alerts).</li>
			<li>Improving the service, debugging, and preventing abuse.</li>
			<li>Complying with applicable laws and lawful requests from authorities.</li>
		</ul>
		<p>We will not use your personal data for a new purpose that is materially different from those listed above without first obtaining your express and voluntary consent, as required by DPP 3.</p>

		<h3>4. How we share data (DPP 3)</h3>
		<p>We do <strong>not</strong> sell your personal data. We share it only in the following circumstances:</p>
		<ul>
			<li><strong>With other users:</strong> your display name, avatar, city, pins, ratings and shared lists are visible to friends; shared lists you generate are accessible to anyone with the public link.</li>
			<li><strong>With service providers (Data Processors):</strong> hosting (AWS, EC2/RDS in the United States), transactional email (Resend), mapping & places data (Google Maps Platform, OpenStreetMap/Nominatim via our backend proxy). They process data on our instructions under contractual safeguards.</li>
			<li><strong>For legal reasons:</strong> when required by a court order, subpoena or other lawful request, including from Hong Kong authorities under the PDPO or other ordinances.</li>
		</ul>

		<h3>5. Cross-border transfer</h3>
		<p>Although Section 33 of the PDPO (regulating transfers of personal data outside Hong Kong) is not yet in force, we apply its spirit voluntarily. Where we transfer data to processors outside Hong Kong (for example, to AWS data centres in the United States or to Resend in the European Union / United States), we ensure that the recipient is bound by written contractual terms to protect the data to a standard substantially similar to the PDPO; data is transmitted using TLS encryption in transit; and the transfer is limited to what is necessary to provide the service.</p>

		<h3>6. Retention (DPP 2)</h3>
		<p>We keep personal data only for as long as is necessary for the purposes set out above. When you delete your account, we delete or anonymise your personal data within 30 days, except where retention is required to comply with a legal obligation, to resolve disputes or to enforce our agreements. Backups containing residual copies are purged on a rolling 90-day cycle.</p>

		<h3>7. Security (DPP 4)</h3>
		<p>We apply reasonable and practicable security measures, including TLS 1.2+ for all traffic, hashed password storage (Django's PBKDF2 default), access controls on our infrastructure, rate-limiting on sensitive endpoints, and logging. No system is perfectly secure; if we become aware of a personal data breach that is likely to result in real risk of significant harm, we will notify affected users and, where appropriate, the PCPD without undue delay.</p>

		<h3>8. Accuracy (DPP 2)</h3>
		<p>You can edit most of your personal data directly from your profile screen. If any data we hold is inaccurate, please correct it in-app or write to us.</p>

		<h3>9. Your rights (DPP 5 & 6)</h3>
		<p>Under the PDPO, you have the right to be informed of our privacy policies and practices (DPP 5); to ascertain whether we hold personal data about you and to request a copy of that data (Data Access Request, s.18 PDPO); to request correction of inaccurate data (Data Correction Request, s.22 PDPO); and to opt out of any direct marketing (we currently send no direct marketing).</p>
		<p>To exercise any of these rights, email <a href="mailto:info@lovemuse.app">info@lovemuse.app</a> from the address linked to your account. We will respond within 40 days, as required by the PDPO. We may charge a reasonable fee for compliance with a Data Access Request, in line with PCPD guidance.</p>

		<h3>10. Complaints</h3>
		<p>If you believe we have failed to comply with the PDPO, you may lodge a complaint with the Office of the Privacy Commissioner for Personal Data, Hong Kong (PCPD), 12/F, Sunlight Tower, 248 Queen's Road East, Wanchai, Hong Kong — <a href="https://www.pcpd.org.hk" rel="noopener" target="_blank">www.pcpd.org.hk</a>.</p>

		<h3>Changes and contact</h3>
		<p>We may update this Policy. Material changes will be notified in-app or by email at least 14 days before they take effect. For any privacy-related question or request, contact us at <a href="mailto:info@lovemuse.app">info@lovemuse.app</a>.</p>
	{/if}
</div>
