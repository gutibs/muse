import { BarcodeFormat, BarcodeScanner } from '@capacitor-mlkit/barcode-scanning';
import { Capacitor } from '@capacitor/core';
import { logSilent } from '$lib/utils/logger';

export type ScanResult =
	| { ok: true; value: string }
	| { ok: false; reason: 'unsupported' | 'no-permission' | 'cancelled' | 'failed' };

/** Abrir la cámara y leer un QR, una sola vez.
 *
 * Todo lo que no sea un código leído sale como un motivo, no como excepción:
 * cancelar el escaneo es el camino más común y no es un error. El plugin no
 * tiene implementación web, así que en el dev server esto contesta
 * `unsupported` en vez de romper — la verificación de verdad es en el
 * teléfono con un APK. */
export async function scanOnce(): Promise<ScanResult> {
	if (!Capacitor.isNativePlatform()) return { ok: false, reason: 'unsupported' };

	try {
		const { supported } = await BarcodeScanner.isSupported();
		if (!supported) return { ok: false, reason: 'unsupported' };

		const { camera } = await BarcodeScanner.requestPermissions();
		if (camera !== 'granted' && camera !== 'limited') {
			return { ok: false, reason: 'no-permission' };
		}

		const { barcodes } = await BarcodeScanner.scan({ formats: [BarcodeFormat.QrCode] });
		const primero = barcodes[0]?.rawValue;
		return primero ? { ok: true, value: primero } : { ok: false, reason: 'cancelled' };
	} catch (err) {
		logSilent('qr-scanner.scanOnce', err);
		return { ok: false, reason: 'failed' };
	}
}
