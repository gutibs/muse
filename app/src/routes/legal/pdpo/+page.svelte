<script lang="ts">
	import { i18n } from '$lib/i18n/index.svelte';
</script>

<div class="legal-doc">
	{#if i18n.locale === 'es'}
		<h2>Política de Privacidad</h2>
		<p class="meta">Última actualización: 18 de mayo de 2026 · Aplicable a los usuarios de Muse (lovemuse.app).</p>

		<p>
			Muse ("nosotros") respeta tu privacidad. Esta Política de Privacidad explica
			qué datos personales recopilamos, cómo los usamos, con quién los compartimos
			y los derechos que te asisten. Está redactada para cumplir con la
			<strong>Personal Data (Privacy) Ordinance (Cap. 486)</strong> de Hong Kong
			("PDPO") y los seis Principios de Protección de Datos ("DPP") emitidos por
			la Office of the Privacy Commissioner for Personal Data, Hong Kong ("PCPD").
		</p>

		<h3>1. Quiénes somos (Data User)</h3>
		<p>Muse opera como un servicio en línea disponible en lovemuse.app y mediante aplicaciones móviles. A los efectos de la PDPO, actuamos como <em>Data User</em> respecto de los datos personales que recopilamos de vos. Los datos de contacto para consultas de privacidad figuran al final de esta Política.</p>

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

		<h3>11. Cambios</h3>
		<p>Podemos actualizar esta Política. Los cambios materiales se notifican dentro de la app o por email con al menos 14 días de antelación. El uso continuado tras la fecha efectiva implica aceptación.</p>

		<h3>12. Contacto</h3>
		<p>Cualquier consulta de privacidad: <a href="mailto:info@lovemuse.app">info@lovemuse.app</a>.</p>

	{:else if i18n.locale === 'it'}
		<h2>Informativa sulla Privacy</h2>
		<p class="meta">Ultimo aggiornamento: 18 maggio 2026 · Valida per gli utenti di Muse (lovemuse.app).</p>

		<p>
			Muse ("noi") rispetta la tua privacy. Questa Informativa spiega quali dati
			personali raccogliamo, come li utilizziamo, con chi li condividiamo e quali
			diritti hai. È redatta in conformità alla
			<strong>Personal Data (Privacy) Ordinance (Cap. 486)</strong> di Hong Kong
			("PDPO") e ai sei Data Protection Principles ("DPP") emanati
			dall'Office of the Privacy Commissioner for Personal Data, Hong Kong ("PCPD").
		</p>

		<h3>1. Chi siamo (Data User)</h3>
		<p>Muse opera come servizio online disponibile su lovemuse.app e tramite applicazioni mobili. Ai fini della PDPO, agiamo come <em>Data User</em> rispetto ai dati personali che raccogliamo. I contatti per richieste sulla privacy sono in fondo a questa Informativa.</p>

		<h3>2. Dati personali che raccogliamo</h3>
		<p>Raccogliamo solo i dati necessari per fornire il servizio:</p>
		<ul>
			<li><strong>Dati dell'account:</strong> email, nome visualizzato, password (con hash), preferenza di lingua.</li>
			<li><strong>Dati del profilo (facoltativi):</strong> biografia, città, preferenze alimentari, cucina preferita, handle Instagram, sito web, telefono, avatar.</li>
			<li><strong>Contenuti creati:</strong> ristoranti contrassegnati come "visitato" o "da visitare", valutazioni, commenti, liste condivise.</li>
			<li><strong>Grafo sociale:</strong> connessioni di amicizia e inviti.</li>
			<li><strong>Dati tecnici del dispositivo:</strong> IP, tipo di dispositivo, sistema operativo, versione dell'app, log di crash, posizione approssimativa o precisa <em>solo</em> con permesso esplicito.</li>
			<li><strong>Comunicazioni:</strong> email che ci invii a <a href="mailto:info@lovemuse.app">info@lovemuse.app</a>.</li>
		</ul>
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

		<h3>11. Modifiche</h3>
		<p>Possiamo aggiornare l'Informativa. Le modifiche sostanziali saranno notificate in app o via email almeno 14 giorni prima.</p>

		<h3>12. Contatto</h3>
		<p>Per qualsiasi domanda sulla privacy: <a href="mailto:info@lovemuse.app">info@lovemuse.app</a>.</p>

	{:else}
		<h2>Privacy Policy</h2>
		<p class="meta">Last updated: 18 May 2026 · Effective for users of Muse (lovemuse.app).</p>

		<p>
			Muse ("we", "us", "our") respects your privacy. This Privacy Policy explains
			what personal data we collect, how we use it, who we share it with, and the
			rights you have. It is written to comply with the
			<strong>Personal Data (Privacy) Ordinance (Cap. 486)</strong> of Hong Kong
			("PDPO") and the six Data Protection Principles ("DPPs") issued by the
			Office of the Privacy Commissioner for Personal Data, Hong Kong ("PCPD").
		</p>

		<h3>1. Who we are (Data User)</h3>
		<p>Muse is operated as an online service available at lovemuse.app and via mobile applications. For the purposes of the PDPO, we act as the <em>Data User</em> in respect of the personal data we collect from you. Contact details for privacy enquiries are set out at the end of this Policy.</p>

		<h3>2. Personal data we collect</h3>
		<p>We collect only the data we need to run the service:</p>
		<ul>
			<li><strong>Account data:</strong> email address, display name, password (stored hashed), language preference.</li>
			<li><strong>Profile data (optional):</strong> bio, city, dietary preferences, favourite cuisine, Instagram handle, website, phone, avatar.</li>
			<li><strong>Content you create:</strong> restaurants you pin as "visited" or "to visit", ratings, comments, shared lists.</li>
			<li><strong>Social graph:</strong> friend connections and invitations you send or accept.</li>
			<li><strong>Device & technical data:</strong> IP address, device type, operating system, app version, crash logs, approximate or precise location <em>only</em> when you explicitly grant the permission.</li>
			<li><strong>Communications:</strong> emails you send to us at <a href="mailto:info@lovemuse.app">info@lovemuse.app</a>.</li>
		</ul>
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

		<h3>11. Changes to this Policy</h3>
		<p>We may update this Policy. Material changes will be notified in-app or by email at least 14 days before they take effect. Continued use after the effective date constitutes acceptance.</p>

		<h3>12. Contact</h3>
		<p>For any privacy-related question or request, contact us at <a href="mailto:info@lovemuse.app">info@lovemuse.app</a>.</p>
	{/if}
</div>
