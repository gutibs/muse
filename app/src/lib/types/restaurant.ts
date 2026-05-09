export interface Cuisine {
	id: number;
	name: string;
	slug: string;
}

export type TagKind = 'dietary' | 'general' | 'highlight';

export interface Tag {
	id: number;
	name: string;
	slug: string;
	kind: TagKind;
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
	phone: string;
	averageRating: number | null;
	pinCount: number;
	approvalStatus: 'pending' | 'approved' | 'rejected';
	createdAt: string;
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
	user: { id: number; displayName: string; avatar: string | null };
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
}
