import { api } from './api.service';
import type {
	AuthTokens,
	LoginRequest,
	Profile,
	RegisterRequest,
	RegisterResponse,
} from '$lib/types';

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

	updateProfile(data: Partial<Pick<Profile, 'displayName' | 'bio' | 'city' | 'website' | 'instagram' | 'dietary' | 'favouriteCuisine'>>): Promise<Profile> {
		return api.patch('/auth/profile/', data);
	},

	changePassword(currentPassword: string, newPassword: string): Promise<void> {
		return api.post('/auth/change-password/', { currentPassword, newPassword });
	},
};
