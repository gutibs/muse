import { fireEvent, render, waitFor } from '@testing-library/svelte';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import ReportModal from './ReportModal.svelte';
import { moderationService } from '$lib/services/moderation.service';

vi.mock('$lib/services/moderation.service', async (orig) => ({
	...(await orig<Record<string, unknown>>()),
	moderationService: { report: vi.fn(), block: vi.fn() }
}));

// La prop se llama `user` y no `target`: `target` es una opción reservada de
// Svelte y testing-library la intercepta antes de llegar al componente.
const TARGET = { id: 7, displayName: 'Fulano' };

function pick(container: HTMLElement, reason: string) {
	const input = container.querySelector(`input[value="${reason}"]`) as HTMLInputElement;
	return fireEvent.click(input);
}

describe('ReportModal', () => {
	beforeEach(() => {
		vi.mocked(moderationService.report).mockReset().mockResolvedValue({ id: 1 });
		vi.mocked(moderationService.block).mockReset().mockResolvedValue({} as never);
	});

	it('offers every reason the backend accepts', () => {
		const { container } = render(ReportModal, { user: TARGET, onclose: () => {} });
		const values = [...container.querySelectorAll('input[name="reason"]')].map(
			(i) => (i as HTMLInputElement).value
		);
		expect(values).toEqual([
			'harassment',
			'spam',
			'inappropriate',
			'impersonation',
			'other'
		]);
	});

	it('cannot submit without choosing a reason', () => {
		const { container } = render(ReportModal, { user: TARGET, onclose: () => {} });
		const submit = container.querySelector('button[type="submit"]') as HTMLButtonElement;
		expect(submit.disabled).toBe(true);
	});

	it('sends the report with reason and detail', async () => {
		const { container } = render(ReportModal, { user: TARGET, onclose: () => {} });
		await pick(container, 'harassment');
		const detail = container.querySelector('textarea') as HTMLTextAreaElement;
		await fireEvent.input(detail, { target: { value: 'me insultó' } });
		await fireEvent.submit(container.querySelector('form') as HTMLFormElement);

		await waitFor(() => {
			expect(moderationService.report).toHaveBeenCalledWith({
				reportedUserId: 7,
				reason: 'harassment',
				detail: 'me insultó'
			});
		});
	});

	it('includes the pin when a review is being reported', async () => {
		const { container } = render(ReportModal, {
			user: TARGET,
			pinId: 99,
			onclose: () => {}
		});
		await pick(container, 'inappropriate');
		await fireEvent.submit(container.querySelector('form') as HTMLFormElement);

		await waitFor(() => {
			expect(moderationService.report).toHaveBeenCalledWith(
				expect.objectContaining({ pinId: 99, reportedUserId: 7 })
			);
		});
	});

	it('offers to block right after reporting', async () => {
		// Quien acaba de denunciar por acoso casi siempre quiere además dejar
		// de ver a esa persona. Que sean dos viajes separados por la app es
		// pedirle que vuelva a buscarla.
		const { container } = render(ReportModal, { user: TARGET, onclose: () => {} });
		await pick(container, 'harassment');
		await fireEvent.submit(container.querySelector('form') as HTMLFormElement);

		await waitFor(() => {
			expect(container.querySelector('[data-testid="block-too"]')).not.toBeNull();
		});

		await fireEvent.click(container.querySelector('[data-testid="block-too"]') as HTMLElement);
		await waitFor(() => expect(moderationService.block).toHaveBeenCalledWith(7));
	});

	it('shows an error and keeps the form when the report fails', async () => {
		vi.mocked(moderationService.report).mockRejectedValue(new Error('boom'));
		const { container } = render(ReportModal, { user: TARGET, onclose: () => {} });
		await pick(container, 'spam');
		await fireEvent.submit(container.querySelector('form') as HTMLFormElement);

		await waitFor(() => {
			expect(container.querySelector('[data-testid="report-error"]')).not.toBeNull();
		});
		expect(container.querySelector('form')).not.toBeNull();
	});
});
