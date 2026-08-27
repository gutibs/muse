import { api } from './api.service';
import type {
	AuthTokens,
	DietaryPreference,
	LoginRequest,
	Profile,
	RegisterRequest,
	RegisterResponse,
} from '$lib/types';

/** Subset of Profile that is writeable. dietaryPreferences carries IDs. */
export type ProfileUpdatePayload = Partial<
	Pick<
		Profile,
		| 'displayName'
		| 'bio'
		| 'city'
		| 'website'
		| 'instagram'
		| 'phone'
		| 'favouriteCuisine'
		| 'analyticsOptOut'
		| 'defaultPinVisibility'
		| 'dietaryPreferences'
	>
>;

export const authService = {
	register(data: RegisterRequest): Promise<RegisterResponse> {
		return api.post('/auth/register/', data);
	},

	login(data: LoginRequest): Promise<AuthTokens> {
		return api.post('/auth/token/', data);
	},

	getProfile(): Promise<Profile> {
		return api.get('/auth/profile/');
	},

	updateProfile(data: ProfileUpdatePayload): Promise<Profile> {
		return api.patch('/auth/profile/', data);
	},

	dietaryPreferences(): Promise<DietaryPreference[]> {
		return api.get('/auth/dietary-preferences/');
	},

	/** Devuelve un par de tokens NUEVO, no 204: el cambio de contraseña
	 * invalida todo lo firmado con el hash anterior, incluido el token de este
	 * mismo dispositivo (CHECK_REVOKE_TOKEN). Quien llame tiene que guardarlo
	 * — de eso se encarga `authStore.changePassword`. */
	changePassword(currentPassword: string, newPassword: string): Promise<AuthTokens> {
		return api.post('/auth/change-password/', { currentPassword, newPassword });
	},

	/** Right to erasure (GDPR art. 17). Irreversible: the account is anonymised
	 * server-side and every token stops working immediately. */
	deleteAccount(currentPassword: string): Promise<void> {
		return api.delete('/auth/profile/', { currentPassword });
	},
};
