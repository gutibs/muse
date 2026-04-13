export interface UserStats {
	pinCount: number;
	visitedCount: number;
	toVisitCount: number;
	friendCount: number;
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
	favouriteCuisine: number | null;
	favouriteCuisineDetail: { id: number; name: string; slug: string } | null;
	dietary: string;
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
