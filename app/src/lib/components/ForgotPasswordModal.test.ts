import { fireEvent, render, waitFor } from '@testing-library/svelte';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import ForgotPasswordModal from './ForgotPasswordModal.svelte';
import { passwordResetService } from '$lib/services/password-reset.service';

vi.mock('$lib/services/password-reset.service', () => ({
	passwordResetService: { requestCode: vi.fn(), confirm: vi.fn() }
}));

const EMAIL = 'forgot@example.com';

function type(container: HTMLElement, selector: string, value: string) {
	const input = container.querySelector(selector) as HTMLInputElement;
	return fireEvent.input(input, { target: { value } });
}

describe('ForgotPasswordModal', () => {
	beforeEach(() => {
		vi.mocked(passwordResetService.requestCode).mockReset().mockResolvedValue({ detail: 'ok' });
		vi.mocked(passwordResetService.confirm).mockReset().mockResolvedValue({ detail: 'ok' });
	});

	it('starts on the email step', () => {
		const { container } = render(ForgotPasswordModal, { onclose: () => {} });
		expect(container.querySelector('input[type="email"]')).not.toBeNull();
		expect(container.querySelector('input[name="code"]')).toBeNull();
	});

	it('moves to the code step after asking for a code', async () => {
		const { container } = render(ForgotPasswordModal, { onclose: () => {} });
		await type(container, 'input[type="email"]', EMAIL);
		await fireEvent.submit(container.querySelector('form') as HTMLFormElement);

		await waitFor(() => {
			expect(container.querySelector('input[name="code"]')).not.toBeNull();
		});
		expect(passwordResetService.requestCode).toHaveBeenCalledWith(EMAIL, expect.anything());
	});

	it('reaches the password step and redeems the code', async () => {
		const { container } = render(ForgotPasswordModal, { onclose: () => {} });
		await type(container, 'input[type="email"]', EMAIL);
		await fireEvent.submit(container.querySelector('form') as HTMLFormElement);
		await waitFor(() => expect(container.querySelector('input[name="code"]')).not.toBeNull());

		await type(container, 'input[name="code"]', '123456');
		await fireEvent.submit(container.querySelector('form') as HTMLFormElement);
		await waitFor(() =>
			expect(container.querySelector('input[name="newPassword"]')).not.toBeNull()
		);

		await type(container, 'input[name="newPassword"]', 'Nu3va-clave-segura!');
		await fireEvent.submit(container.querySelector('form') as HTMLFormElement);

		await waitFor(() => {
			expect(passwordResetService.confirm).toHaveBeenCalledWith(
				EMAIL,
				'123456',
				'Nu3va-clave-segura!'
			);
		});
	});

	it('advances even when the account does not exist', async () => {
		// El backend responde 200 exista o no la cuenta. Si la app se
		// adelantara a mostrar "te mandamos el código" sólo en algún caso,
		// reintroduciría por la UI el oráculo de enumeración que el backend
		// cierra.
		const { container } = render(ForgotPasswordModal, { onclose: () => {} });
		await type(container, 'input[type="email"]', 'nobody@example.com');
		await fireEvent.submit(container.querySelector('form') as HTMLFormElement);

		await waitFor(() => expect(container.querySelector('input[name="code"]')).not.toBeNull());
	});

	it('shows an error and stays on the code step when the code is rejected', async () => {
		const { ApiError } = await import('$lib/types');
		vi.mocked(passwordResetService.confirm).mockRejectedValue(
			new ApiError(400, { code: ['Invalid or expired code.'] })
		);

		const { container } = render(ForgotPasswordModal, { onclose: () => {} });
		await type(container, 'input[type="email"]', EMAIL);
		await fireEvent.submit(container.querySelector('form') as HTMLFormElement);
		await waitFor(() => expect(container.querySelector('input[name="code"]')).not.toBeNull());
		await type(container, 'input[name="code"]', '000000');
		await fireEvent.submit(container.querySelector('form') as HTMLFormElement);
		await waitFor(() =>
			expect(container.querySelector('input[name="newPassword"]')).not.toBeNull()
		);
		await type(container, 'input[name="newPassword"]', 'Nu3va-clave-segura!');
		await fireEvent.submit(container.querySelector('form') as HTMLFormElement);

		await waitFor(() => {
			expect(container.querySelector('[data-testid="reset-error"]')).not.toBeNull();
		});
		expect(container.querySelector('input[name="newPassword"]')).not.toBeNull();
	});

	it('lets the user go back and ask for another code', async () => {
		const { container } = render(ForgotPasswordModal, { onclose: () => {} });
		await type(container, 'input[type="email"]', EMAIL);
		await fireEvent.submit(container.querySelector('form') as HTMLFormElement);
		await waitFor(() => expect(container.querySelector('input[name="code"]')).not.toBeNull());

		await fireEvent.click(container.querySelector('[data-testid="resend-code"]') as HTMLElement);

		await waitFor(() => expect(passwordResetService.requestCode).toHaveBeenCalledTimes(2));
	});
});
