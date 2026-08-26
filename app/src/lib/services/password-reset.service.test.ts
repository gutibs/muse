import { beforeEach, describe, expect, it, vi } from 'vitest';
import { api } from './api.service';
import { passwordResetService } from './password-reset.service';

vi.mock('./api.service', () => ({
	api: { postAnon: vi.fn() }
}));

describe('passwordResetService', () => {
	beforeEach(() => {
		vi.mocked(api.postAnon).mockReset();
		vi.mocked(api.postAnon).mockResolvedValue({ detail: 'ok' });
	});

	it('asks for a code with the email and the current language', async () => {
		await passwordResetService.requestCode('forgot@example.com', 'it');

		expect(api.postAnon).toHaveBeenCalledWith('/auth/password-reset/', {
			email: 'forgot@example.com',
			language: 'it'
		});
	});

	it('redeems the code with the new password, in the user language', async () => {
		// El idioma viaja para que los errores de validación de contraseña
		// vuelvan traducidos: la API no tiene LocaleMiddleware y Django
		// contesta en español por defecto.
		await passwordResetService.confirm('forgot@example.com', '123456', 'Nu3va-clave!', 'it');

		expect(api.postAnon).toHaveBeenCalledWith('/auth/password-reset/confirm/', {
			email: 'forgot@example.com',
			code: '123456',
			newPassword: 'Nu3va-clave!',
			language: 'it'
		});
	});

	it('goes out anonymously, never through the authenticated post', async () => {
		// Verificado contra el backend: un endpoint AllowAny igual responde 401
		// si el header trae un token inválido, porque la autenticación corre
		// antes que el permiso. Con un token muerto guardado —que es
		// exactamente lo que deja el deploy de CHECK_REVOKE_TOKEN— api.post
		// dispararía un refresh fallido y un clearAuth en medio del flujo que
		// existe justamente porque la persona no puede entrar.
		await passwordResetService.requestCode('forgot@example.com');
		await passwordResetService.confirm('forgot@example.com', '123456', 'Nu3va-clave!');

		expect(api.postAnon).toHaveBeenCalledTimes(2);
		expect((api as Record<string, unknown>).post).toBeUndefined();
	});
});
