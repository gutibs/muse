export interface Cuisine {
	id: number;
	name: string;
	slug: string;
}

/** `vibe`, `occasion` y `scene` son los tres ejes con los que alguien
 * describe un lugar al guardarlo; los otros tres son atributos del
 * restaurante en sí. */
export type TagKind = 'dietary' | 'general' | 'highlight' | 'vibe' | 'occasion' | 'scene';

export interface Tag {
	id: number;
	name: string;
	slug: string;
	kind: TagKind;
}

/** Autor de la foto de Google. Los términos exigen mostrarlo junto a la foto. */
export interface PhotoAttribution {
	displayName: string;
	uri: string;
}

export type ReservationProvider =
	| 'opentable'
	| 'thefork'
	| 'resy'
	| 'sevenrooms'
	| 'quandoo'
	| 'tablecheck'
	| 'meitre'
	| 'direct'
	| 'other';

export interface Reservation {
	url: string;
	provider: ReservationProvider;
}

export interface Restaurant {
	id: number;
	name: string;
	lat: number;
	lng: number;
	address: string;
	city: string;
	country: string;
	imageUrl: string;
	cuisines: number[];
	cuisinesDetail: Cuisine[];
	tagsDetail: Tag[];
	priceLevel: number | null;
	qualityLevel: number | null;
	website: string;
	/**
	 * Link de reserva, o `null` mientras esté pendiente de revisión. El
	 * backend no lo manda hasta que el dominio pasó la clasificación: lo
	 * escribe un usuario y se le muestra a todos los demás.
	 */
	reservation: Reservation | null;
	phone: string;
	averageRating: number | null;
	pinCount: number;
	approvalStatus: 'pending' | 'approved' | 'rejected';
	/** El lugar cerró para siempre. Sigue accesible desde un pin, pero no
	 * aparece en búsqueda ni en "cerca mío". */
	isClosed: boolean;
	createdAt: string;
	/** Sólo viene en el detalle: en el listado sería un lookup por fila. */
	photoAttribution?: PhotoAttribution[];
}

export interface MenuItem {
	id: number;
	name: string;
	description: string;
	price: number | null;
	currency: string;
	category: 'starter' | 'main' | 'dessert' | 'drink' | 'side';
	/**
	 * Replaces the old isRecommended/isVegetarian/isGlutenFree booleans.
	 * Filter by `tag.kind === 'dietary'` for dietary badges, `'highlight'`
	 * for "recommended"-style flair.
	 */
	tags: Tag[];
	imageUrl: string;
}

export interface Review {
	id: number;
	/** Same shape the API uses for a user everywhere else (no email: reviews
	 * are public to non-friends by design). `isDeleted` means the author
	 * erased their account — render the localised "anonymous" label instead
	 * of the byline. See accounts.services.account_deletion. */
	user: {
		id: number;
		displayName: string;
		avatar: string | null;
		city: string;
		isDeleted: boolean;
	};
	rating: number;
	comment: string;
	visitedAt: string | null;
	createdAt: string;
	isFriend: boolean;
}

export interface FriendStats {
	ratingAvg: number | null;
	ratedCount: number;
	onListCount: number;
}

export interface RestaurantDetail extends Restaurant {
	menuItems: MenuItem[];
	reviews: Review[];
	friendStats: FriendStats;
}

export interface RestaurantCreate {
	name: string;
	latitude: number;
	longitude: number;
	address?: string;
	city?: string;
	country?: string;
	cuisines?: number[];
	tagIds?: number[];
	priceLevel?: number;
	qualityLevel?: number;
	/** Se guarda siempre; se muestra sólo si el dominio pasa la revisión. */
	reservationUrl?: string;
}
