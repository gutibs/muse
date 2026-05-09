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

	changePassword(currentPassword: string, newPassword: string): Promise<void> {
		return api.post('/auth/change-password/', { currentPassword, newPassword });
	},
};
