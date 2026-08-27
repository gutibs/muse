import { api } from './api.service';

/** Recuperación de contraseña por código de 6 dígitos.
 *
 * Las dos llamadas van por `postAnon` a propósito: los endpoints son
 * anónimos, pero DRF corre la autenticación antes que el permiso, así que un
 * token inválido en el header devuelve 401 igual. Quien usa este flujo es
 * justamente quien no puede entrar —y después del deploy que activa
 * CHECK_REVOKE_TOKEN todo el mundo tiene un token muerto guardado—, así que
 * mandar el header rompería el flujo y encima desloguearía.
 */
export const passwordResetService = {
	/** Pide un código al email. Responde igual exista o no la cuenta: no hay
	 * nada en la respuesta que permita saberlo, y eso es deliberado. */
	requestCode(email: string, language?: string): Promise<{ detail: string }> {
		return api.postAnon('/auth/password-reset/', { email, language });
	},

	/** Canjea el código por una contraseña nueva. Un 400 con la clave `code`
	 * puede ser código errado, vencido, quemado o ya usado: el backend no
	 * distingue, a propósito. El idioma va para que los errores de validación
	 * de la contraseña vuelvan traducidos — la API no tiene LocaleMiddleware,
	 * así que Django contesta en español si nadie le dice otra cosa. */
	confirm(
		email: string,
		code: string,
		newPassword: string,
		language?: string
	): Promise<{ detail: string }> {
		return api.postAnon('/auth/password-reset/confirm/', {
			email,
			code,
			newPassword,
			language
		});
	}
};
