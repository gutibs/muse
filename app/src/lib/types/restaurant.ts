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
	cuisine: number | null;
	cuisineDetail: Cuisine | null;
	tagsDetail: Tag[];
	priceLevel: number | null;
	qualityLevel: number | null;
	website: string;
	phone: string;
	averageRating: number | null;
	pinCount: number;
	createdAt: string;
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
