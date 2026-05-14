import { Capacitor } from '@capacitor/core';
import { Geolocation, type Position } from '@capacitor/geolocation';

export type GeoErrorCode =
	| 'permission_denied'
	| 'position_unavailable'
	| 'timeout'
	| 'not_available'
	| 'unknown';

export class GeoError extends Error {
	code: GeoErrorCode;
	constructor(code: GeoErrorCode, message?: string) {
		super(message ?? code);
		this.code = code;
	}
}

export interface GeoPosition {
	latitude: number;
	longitude: number;
	accuracy: number;
}

interface GeolocateOptions {
	enableHighAccuracy?: boolean;
	timeout?: number;
	maximumAge?: number;
}

function fromCapacitor(p: Position): GeoPosition {
	return {
		latitude: p.coords.latitude,
		longitude: p.coords.longitude,
		accuracy: p.coords.accuracy,
	};
}

function fromBrowser(p: GeolocationPosition): GeoPosition {
	return {
		latitude: p.coords.latitude,
		longitude: p.coords.longitude,
		accuracy: p.coords.accuracy,
	};
}

function mapBrowserError(err: GeolocationPositionError): GeoError {
	if (err.code === err.PERMISSION_DENIED) return new GeoError('permission_denied', err.message);
	if (err.code === err.POSITION_UNAVAILABLE)
		return new GeoError('position_unavailable', err.message);
	if (err.code === err.TIMEOUT) return new GeoError('timeout', err.message);
	return new GeoError('unknown', err.message);
}

function mapCapacitorError(err: unknown): GeoError {
	const msg = err instanceof Error ? err.message : String(err);
	const lower = msg.toLowerCase();
	if (lower.includes('denied') || lower.includes('not granted'))
		return new GeoError('permission_denied', msg);
	if (lower.includes('unavailable') || lower.includes('disabled'))
		return new GeoError('position_unavailable', msg);
	if (lower.includes('timeout')) return new GeoError('timeout', msg);
	return new GeoError('unknown', msg);
}

export async function getCurrentPosition(opts: GeolocateOptions = {}): Promise<GeoPosition> {
	const { enableHighAccuracy = true, timeout = 10000, maximumAge = 60000 } = opts;

	if (Capacitor.isNativePlatform()) {
		try {
			const perm = await Geolocation.checkPermissions();
			if (perm.location !== 'granted') {
				const req = await Geolocation.requestPermissions({ permissions: ['location'] });
				if (req.location !== 'granted') {
					throw new GeoError('permission_denied', 'Location permission not granted');
				}
			}
			const pos = await Geolocation.getCurrentPosition({
				enableHighAccuracy,
				timeout,
				maximumAge,
			});
			return fromCapacitor(pos);
		} catch (err) {
			if (err instanceof GeoError) throw err;
			throw mapCapacitorError(err);
		}
	}

	if (typeof navigator === 'undefined' || !navigator.geolocation) {
		throw new GeoError('not_available', 'Geolocation API not available');
	}

	return new Promise<GeoPosition>((resolve, reject) => {
		navigator.geolocation.getCurrentPosition(
			(p) => resolve(fromBrowser(p)),
			(err) => reject(mapBrowserError(err)),
			{ enableHighAccuracy, timeout, maximumAge },
		);
	});
}
