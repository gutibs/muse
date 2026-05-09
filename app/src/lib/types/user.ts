export interface UserStats {
	pinCount: number;
	visitedCount: number;
	toVisitCount: number;
	friendCount: number;
}

export interface DietaryPreference {
	id: number;
	name: string;
	slug: string;
}

export interface Profile {
	id: number;
	email: string;
	displayName: string;
	bio: string;
	avatar: string | null;
	city: string;
	website: string;
	instagram: string;
	phone: string;
	favouriteCuisine: number | null;
	favouriteCuisineDetail: { id: number; name: string; slug: string } | null;
	/** PKs of selected DietaryPreference rows. Used as the write payload. */
	dietaryPreferences: number[];
	/** Hydrated detail (read-only); render this in the UI. */
	dietaryPreferencesDetail: DietaryPreference[];
	stats: UserStats;
	createdAt: string;
}

export interface PublicUser {
	id: number;
	email: string;
	displayName: string;
	avatar: string | null;
	city: string;
}

export type FriendshipStatus = 'pending' | 'accepted' | 'declined';

export interface Friendship {
	id: number;
	fromUser: PublicUser;
	toUser: PublicUser;
	status: FriendshipStatus;
	createdAt: string;
}

export interface AuthTokens {
	access: string;
	refresh: string;
}

export interface RegisterResponse {
	user: Profile;
	tokens: AuthTokens;
}

export interface LoginRequest {
	username: string;
	password: string;
}

export interface RegisterRequest {
	email: string;
	password: string;
	displayName?: string;
}
