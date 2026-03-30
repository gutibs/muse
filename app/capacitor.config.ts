import type { CapacitorConfig } from '@capacitor/cli';

const config: CapacitorConfig = {
	appId: 'app.muse.mobile',
	appName: 'Muse',
	webDir: 'build',
	ios: {
		contentInset: 'automatic',
		scrollEnabled: false,
		preferredContentMode: 'mobile'
	}
};

export default config;
