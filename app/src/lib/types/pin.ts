import type { Restaurant, Tag } from './restaurant';

export type PinStatus = 'visited' | 'to_visit';

/**
 * Quién ve este pin. `null` en `Pin.visibility` no es un cuarto valor: quiere
 * decir "lo que diga el default de mi perfil" (ver `pin-visibility.ts`).
 */
export type PinVisibility = 'public' | 'friends' | 'private';

export interface Pin {
	id: number;
	restaurant: number;
	restaurantDetail: Restaurant;
	status: PinStatus;
	rating: number | null;
	comment: string;
	visitedAt: string | null;
	tagsDetail: Tag[];
	/** Marca privada del dueño del pin. No viaja en los links compartidos. */
	isFavourite: boolean;
	/** `null` = heredá el `defaultPinVisibility` del perfil. */
	visibility: PinVisibility | null;
	createdAt: string;
	updatedAt: string;
}

export interface PinCreate {
	restaurant: number;
	status: PinStatus;
	rating?: number;
	comment?: string;
	visitedAt?: string;
	tagIds?: number[];
	/** Omitirlo deja el pin heredando el default del perfil. */
	visibility?: PinVisibility;
}

export type SharedListFilter = 'all' | 'visited' | 'to_visit';

export type SharedListKind = 'auto' | 'curated';

export interface SharedListItem {
	pin: number;
	position: number;
	note: string;
}

export interface SharedList {
	id: number;
	token: string;
	title: string;
	/** `auto` sigue un filtro; `curated` muestra sólo los pins elegidos. */
	kind: SharedListKind;
	statusFilter: SharedListFilter;
	isActive: boolean;
	/** ISO, o null si el link no vence. */
	expiresAt: string | null;
	items: SharedListItem[];
	url: string;
	createdAt: string;
}

// The share-link endpoint has its own narrower serializers on the backend
// (pins/serializers_public.py) so that widening an internal serializer can
// never widen the anonymous payload. These types mirror them exactly — if a
// field is missing here, it is missing on purpose, not by oversight.
export interface PublicRestaurant {
	id: number;
	name: string;
	city: string;
	district: string;
	address: string;
	imageUrl: string;
	priceLevel: number | null;
	// Non-null like on Restaurant: the backing column is NOT NULL, the
	// serializer's None branch is defensive only.
	lat: number;
	lng: number;
}

export interface PublicPin {
	restaurantDetail: PublicRestaurant;
	/** Sólo en listas curadas: lo que el dueño escribió sobre ese lugar. */
	note?: string;
	tagsDetail: Omit<Tag, 'id'>[];
	status: PinStatus;
	rating: number | null;
	comment: string;
}

export interface SharedListPublic {
	id: number;
	title: string;
	// No email here on purpose: this payload comes from the unauthenticated
	// share-link endpoint, which anyone the link reaches can read.
	owner: {
		id: number;
		displayName: string;
		avatar: string | null;
		city: string;
		isDeleted: boolean;
	};
	pins: PublicPin[];
	createdAt: string;
}
