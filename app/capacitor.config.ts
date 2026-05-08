import type { CapacitorConfig } from '@capacitor/cli';

const config: CapacitorConfig = {
	appId: 'app.muse.mobile',
	appName: 'Muse',
	webDir: 'build',
	// Live-reload mode: when CAP_LIVE_RELOAD env var is "1", point the
	// WebView at the local Vite dev server instead of the bundled assets.
	// 10.0.2.2 is the Android emulator alias for the host machine; iOS
	// simulator uses localhost directly.
	// In bundled mode we use androidScheme:'http' so fetch() to
	// http://10.0.2.2:8001 isn't blocked as mixed-content (Capacitor's
	// default https://localhost origin would block any plain-http request).
	server: process.env.CAP_LIVE_RELOAD === '1'
		? {
				url: process.env.CAP_DEV_URL ?? 'http://10.0.2.2:5174',
				cleartext: true,
		  }
		: { androidScheme: 'http' },
	android: {
		allowMixedContent: true,
		webContentsDebuggingEnabled: true
	},
	ios: {
		contentInset: 'automatic',
		scrollEnabled: false,
		preferredContentMode: 'mobile'
	}
};

export default config;
