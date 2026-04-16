export interface Cuisine {
	id: number;
	name: string;
	slug: string;
}

export interface Tag {
	id: number;
	name: string;
	slug: string;
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
	cuisine: number | null;
	cuisineDetail: Cuisine | null;
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
	isRecommended: boolean;
	isVegetarian: boolean;
	isGlutenFree: boolean;
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
	cuisine?: number;
	tagIds?: number[];
	priceLevel?: number;
	qualityLevel?: number;
}
