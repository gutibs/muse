import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { trackVisibility } from './track-visibility';

type Cb = (entries: { isIntersecting: boolean }[]) => void;

let callbacks: Cb[] = [];
const disconnect = vi.fn();

class FakeObserver {
	constructor(cb: Cb) {
		callbacks.push(cb);
	}
	observe() {}
	disconnect = disconnect;
}

describe('trackVisibility', () => {
	beforeEach(() => {
		vi.useFakeTimers();
		callbacks = [];
		disconnect.mockClear();
		vi.stubGlobal('IntersectionObserver', FakeObserver);
	});

	afterEach(() => {
		vi.useRealTimers();
		vi.unstubAllGlobals();
	});

	function mount(onVisible?: () => void) {
		const node = document.createElement('div');
		return trackVisibility(node, { onVisible })!;
	}

	it('counts a card that stayed on screen', () => {
		const onVisible = vi.fn();
		mount(onVisible);

		callbacks[0]([{ isIntersecting: true }]);
		vi.advanceTimersByTime(500);

		expect(onVisible).toHaveBeenCalledTimes(1);
	});

	it('does not count a card that flew past under the thumb', () => {
		const onVisible = vi.fn();
		mount(onVisible);

		callbacks[0]([{ isIntersecting: true }]);
		vi.advanceTimersByTime(200);
		callbacks[0]([{ isIntersecting: false }]);
		vi.advanceTimersByTime(1000);

		expect(onVisible).not.toHaveBeenCalled();
	});

	it('reports once and stops observing', () => {
		const onVisible = vi.fn();
		mount(onVisible);

		callbacks[0]([{ isIntersecting: true }]);
		vi.advanceTimersByTime(500);
		callbacks[0]([{ isIntersecting: true }]);
		vi.advanceTimersByTime(500);

		expect(onVisible).toHaveBeenCalledTimes(1);
		expect(disconnect).toHaveBeenCalled();
	});

	it('does nothing without a callback', () => {
		mount(undefined);
		expect(callbacks).toHaveLength(0);
	});
});
