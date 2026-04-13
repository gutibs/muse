import type { Restaurant } from './restaurant';

export type PinStatus = 'visited' | 'to_visit';

export interface Persona {
	id: number;
	name: string;
	slug: string;
	icon: string;
	color: string;
}

export interface Pin {
	id: number;
	restaurant: number;
	restaurantDetail: Restaurant;
	status: PinStatus;
	rating: number | null;
	comment: string;
	visitedAt: string | null;
	personasDetail: Persona[];
	createdAt: string;
	updatedAt: string;
}

export interface PinCreate {
	restaurant: number;
	status: PinStatus;
	rating?: number;
	comment?: string;
	visitedAt?: string;
	personaIds?: number[];
}

export type SharedListFilter = 'all' | 'visited' | 'to_visit';

export interface SharedList {
	id: number;
	token: string;
	title: string;
	statusFilter: SharedListFilter;
	isActive: boolean;
	url: string;
	createdAt: string;
}

export interface SharedListPublic {
	id: number;
	title: string;
	owner: {
		id: number;
		email: string;
		displayName: string;
		avatar: string | null;
		city: string;
	};
	pins: Pin[];
	createdAt: string;
}
