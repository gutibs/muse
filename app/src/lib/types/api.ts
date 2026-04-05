export interface PaginatedResponse<T> {
	count: number;
	next: string | null;
	previous: string | null;
	results: T[];
}

export class ApiError extends Error {
	status: number;
	data: unknown;

	constructor(status: number, data: unknown) {
		super(`API Error: ${status}`);
		this.status = status;
		this.data = data;
	}
}

export class AuthError extends ApiError {
	constructor() {
		super(401, { detail: 'Authentication required' });
	}
}
