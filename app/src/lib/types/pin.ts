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
