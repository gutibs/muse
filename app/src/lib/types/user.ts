import type { PinVisibility } from './pin';

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
	/** Derecho de oposición (art. 21 GDPR): con esto en true no se registra
	 * ningún evento de uso de esta cuenta, ni desde la app ni desde el servidor. */
	analyticsOptOut: boolean;
	/** Nivel que heredan los pins que no eligieron el suyo. */
	defaultPinVisibility: PinVisibility;
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

/** La forma que devuelve `UserAnonymousSafeSerializer`: sin email, para donde
 * el que mira no necesariamente tiene relación con la persona (reseñas
 * públicas, el `targetUser` de una actividad de amistad, links compartidos).
 * `isDeleted` significa que borró su cuenta: hay que mostrar el label
 * "anónimo" traducido en lugar del nombre. */
export interface AnonymousUser {
	id: number;
	displayName: string;
	avatar: string | null;
	city: string;
	isDeleted: boolean;
}

export type FriendshipStatus = 'pending' | 'accepted' | 'declined';

export interface Friendship {
	id: number;
	fromUser: AnonymousUser;
	toUser: AnonymousUser;
	status: FriendshipStatus;
	createdAt: string;
}

export interface AuthTokens {
	access: string;
	refresh: string;
}

/** El alta no devuelve sesión ni datos: responde lo mismo exista o no la
 * cuenta, porque los únicos tokens posibles para un email ya tomado serían los
 * de esa cuenta. Se entra por el login. */
export interface RegisterResponse {
	detail: string;
}

export interface LoginRequest {
	username: string;
	password: string;
}

export interface RegisterRequest {
	email: string;
	password: string;
	displayName?: string;
	// Active consent — a single unified privacy checkbox, required true; the
	// parser converts to snake_case (accept_privacy) for the backend, which
	// still records one ConsentRecord per framework (GDPR + PDPO).
	acceptPrivacy: boolean;
}
