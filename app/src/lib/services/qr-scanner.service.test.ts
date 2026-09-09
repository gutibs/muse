import { describe, expect, it, vi, beforeEach } from 'vitest';

const scan = vi.fn();
const requestPermissions = vi.fn();
const isSupported = vi.fn();

vi.mock('@capacitor-mlkit/barcode-scanning', () => ({
	BarcodeScanner: {
		scan: (...a: unknown[]) => scan(...a),
		requestPermissions: (...a: unknown[]) => requestPermissions(...a),
		isSupported: (...a: unknown[]) => isSupported(...a)
	},
	BarcodeFormat: { QrCode: 'QR_CODE' }
}));

const isNativePlatform = vi.fn();
vi.mock('@capacitor/core', () => ({ Capacitor: { isNativePlatform: () => isNativePlatform() } }));

const { scanOnce } = await import('./qr-scanner.service');

describe('scanOnce', () => {
	beforeEach(() => {
		vi.clearAllMocks();
		isNativePlatform.mockReturnValue(true);
		isSupported.mockResolvedValue({ supported: true });
		requestPermissions.mockResolvedValue({ camera: 'granted' });
	});

	it('devuelve el texto del primer código leído', async () => {
		scan.mockResolvedValue({ barcodes: [{ rawValue: 'muse://friend/abc' }] });

		await expect(scanOnce()).resolves.toEqual({ ok: true, value: 'muse://friend/abc' });
	});

	it('fuera del teléfono no intenta abrir la cámara', async () => {
		isNativePlatform.mockReturnValue(false);

		await expect(scanOnce()).resolves.toEqual({ ok: false, reason: 'unsupported' });
		expect(scan).not.toHaveBeenCalled();
	});

	it('sin permiso de cámara no escanea', async () => {
		requestPermissions.mockResolvedValue({ camera: 'denied' });

		await expect(scanOnce()).resolves.toEqual({ ok: false, reason: 'no-permission' });
		expect(scan).not.toHaveBeenCalled();
	});

	it('cancelar sin leer nada no es un error', async () => {
		scan.mockResolvedValue({ barcodes: [] });

		await expect(scanOnce()).resolves.toEqual({ ok: false, reason: 'cancelled' });
	});
});
