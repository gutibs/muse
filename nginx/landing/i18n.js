(function () {
	var LOCALE_KEY = 'muse_locale';
	var SUPPORTED = ['en', 'es', 'it'];

	var T = {
		es: {
			title: "Muse — Descubrí restaurantes con amigos",
			description: "Muse — descubrí y compartí restaurantes con amigos.",
			tagline: "Descubrí y compartí restaurantes con amigos.",
			androidText: "Escaneá el QR o tocá el botón para descargar la app.",
			qrAlt: "QR para descargar Muse en Android",
			androidBtn: "Descargá para Android",
			soon: "Próximamente",
			iosText: "Estamos trabajando en la versión para iPhone.",
			back: "← Volver a Muse",
			footerHome: "Inicio",
			footerPrivacy: "Privacidad",
			footerTerms: "Términos",
			footerCommunity: "Comunidad",
			footerCookies: "Cookies",
			footerContact: "Contacto"
		},
		it: {
			title: "Muse — Scopri ristoranti con gli amici",
			description: "Muse — scopri e condividi ristoranti con gli amici.",
			tagline: "Scopri e condividi ristoranti con gli amici.",
			androidText: "Scansiona il QR o tocca il pulsante per scaricare l'app.",
			qrAlt: "QR per scaricare Muse su Android",
			androidBtn: "Scarica per Android",
			soon: "Prossimamente",
			iosText: "Stiamo lavorando alla versione per iPhone.",
			back: "← Torna a Muse",
			footerHome: "Home",
			footerPrivacy: "Privacy",
			footerTerms: "Termini",
			footerCommunity: "Comunità",
			footerCookies: "Cookie",
			footerContact: "Contatto"
		},
		en: {
			title: "Muse — Discover restaurants with friends",
			description: "Muse — discover and share restaurants with friends.",
			tagline: "Discover and share restaurants with friends.",
			androidText: "Scan the QR or tap the button to download the app.",
			qrAlt: "QR code to download Muse on Android",
			androidBtn: "Download for Android",
			soon: "Coming soon",
			iosText: "We're working on the iPhone version.",
			back: "← Back to Muse",
			footerHome: "Home",
			footerPrivacy: "Privacy",
			footerTerms: "Terms",
			footerCommunity: "Community",
			footerCookies: "Cookies",
			footerContact: "Contact"
		}
	};

	function detectInitial() {
		try {
			var saved = localStorage.getItem(LOCALE_KEY);
			if (saved && SUPPORTED.indexOf(saved) !== -1) return saved;
		} catch (_) { /* localStorage may be blocked */ }
		var nav = (navigator.language || 'en').toLowerCase().split('-')[0];
		return SUPPORTED.indexOf(nav) !== -1 ? nav : 'en';
	}

	function apply(locale) {
		var t = T[locale] || T.en;
		document.documentElement.lang = locale;
		if (t.title) document.title = t.title;
		var meta = document.querySelector('meta[name="description"]');
		if (meta && t.description) meta.setAttribute('content', t.description);

		document.querySelectorAll('[data-i18n]').forEach(function (el) {
			var k = el.getAttribute('data-i18n');
			if (t[k]) el.textContent = t[k];
		});
		document.querySelectorAll('[data-i18n-alt]').forEach(function (el) {
			var k = el.getAttribute('data-i18n-alt');
			if (t[k]) el.setAttribute('alt', t[k]);
		});

		// Toggle language-scoped content blocks (used in legal pages).
		document.querySelectorAll('[data-lang]').forEach(function (el) {
			el.hidden = el.getAttribute('data-lang') !== locale;
		});

		// Update active state on language pickers.
		document.querySelectorAll('.lang-picker [data-lang-btn]').forEach(function (btn) {
			var active = btn.getAttribute('data-lang-btn') === locale;
			btn.classList.toggle('active', active);
			btn.setAttribute('aria-pressed', active ? 'true' : 'false');
		});

		document.documentElement.classList.add('i18n-ready');
	}

	function setLocale(locale) {
		if (SUPPORTED.indexOf(locale) === -1) return;
		try { localStorage.setItem(LOCALE_KEY, locale); } catch (_) { /* ignore */ }
		current = locale;
		apply(locale);
	}

	var current = detectInitial();

	// Apply on DOMContentLoaded (in case the script is loaded in <head>).
	if (document.readyState === 'loading') {
		document.addEventListener('DOMContentLoaded', function () { apply(current); });
	} else {
		apply(current);
	}

	window.Muse = window.Muse || {};
	window.Muse.i18n = {
		setLocale: setLocale,
		get locale() { return current; }
	};
})();
