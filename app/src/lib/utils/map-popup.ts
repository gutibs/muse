import type { Pin, PublicUser, Restaurant } from '$lib/types';
import { escapeHtml } from './escape-html';

/**
 * Owner byline source. We accept the partial shape because:
 * - friend pins on the map use `PublicUser` (displayName + email)
 * - shared lists use `SharedListPublic.owner` which is the same shape
 * Avoiding the full type lets the test harness pass plain objects.
 */
export interface PopupOwner {
	displayName?: string | null;
	email?: string | null;
}

export interface PopupOptions {
	restaurant: Pick<Restaurant, 'id' | 'name' | 'city' | 'averageRating' | 'cuisinesDetail'>;
	/**
	 * If present, rating renders as `pin.rating/5` (user's own rating).
	 * If absent and `restaurant.averageRating` is non-null, renders as the
	 * aggregate average (search variant). To force one mode, pass `null`
	 * for the field you want to suppress.
	 */
	pin?: Pick<Pin, 'rating' | 'status'> | null;
	owner?: PopupOwner | null;
	/** Wrap the name in `<a href="/restaurant/${id}">`. Default: false. */
	link?: boolean;
	/**
	 * i18n-resolved label rendered at the bottom (e.g. "Rated" / "On List").
	 * The map's own-pin variant is the only consumer today.
	 */
	statusLabel?: string;
	/** Show comma-separated cuisine names. Used by the search variant. */
	showCuisines?: boolean;
	/**
	 * Pre-built dietary badge HTML to append. Pass the result of
	 * `dietaryBadgesHtml(restaurant.tagsDetail)` from the call site so this
	 * util doesn't need to know about the badge whitelist.
	 */
	dietaryHtml?: string;
}

/**
 * Build the inner HTML for a Leaflet marker popup.
 * Single source of truth for popup design — any visual change happens here.
 *
 * Style notes (kept identical to all 4 pre-existing inline copies):
 *   font: Inter, sans-serif
 *   ink: #2B221A (name)  /  gray: #9A8E7E (city/cuisines/status)
 *   accent rating: #8A7363  /  owner byline: #AF9483
 */
export function buildRestaurantPopup(opts: PopupOptions): string {
	const { restaurant: r, pin, owner, link, statusLabel, showCuisines, dietaryHtml } = opts;

	const name = escapeHtml(r.name ?? '');
	const city = r.city ? escapeHtml(r.city) : '';

	const parts: string[] = [];
	parts.push('<div style="font-family:Inter,sans-serif;min-width:140px;">');

	if (owner) {
		const ownerName = escapeHtml(owner.displayName || owner.email || '');
		if (ownerName) {
			parts.push(
				`<span style="color:#AF9483;font-size:11px;font-weight:600;">${ownerName}</span><br>`
			);
		}
	}

	if (link && r.id != null) {
		parts.push(
			`<a href="/restaurant/${r.id}" style="font-size:14px;font-weight:700;color:#2B221A;text-decoration:none;">${name}</a>`
		);
	} else {
		parts.push(`<strong style="font-size:14px;color:#2B221A;">${name}</strong>`);
	}

	if (city) {
		parts.push(`<br><span style="color:#9A8E7E;font-size:12px;">${city}</span>`);
	}

	if (showCuisines && r.cuisinesDetail?.length) {
		const cuisines = escapeHtml(r.cuisinesDetail.map((c) => c.name).join(', '));
		parts.push(`<br><span style="color:#9A8E7E;font-size:11px;">${cuisines}</span>`);
	}

	// Rating: pin.rating wins if pin is provided; otherwise fall back to
	// the restaurant average. `pin: null` explicitly suppresses both.
	if (pin === undefined) {
		if (r.averageRating != null) {
			parts.push(
				`<br><span style="color:#8A7363;font-size:13px;">♥ ${r.averageRating.toFixed(1)}</span>`
			);
		}
	} else if (pin && pin.rating != null) {
		parts.push(
			`<br><span style="color:#8A7363;font-size:13px;">♥ ${pin.rating}/5</span>`
		);
	}

	if (statusLabel) {
		parts.push(
			`<br><span style="color:#9A8E7E;font-size:11px;">${escapeHtml(statusLabel)}</span>`
		);
	}

	if (dietaryHtml) {
		parts.push(dietaryHtml);
	}

	parts.push('</div>');
	return parts.join('');
}

/**
 * Convenience overload: callers that want only an owner byline can build
 * a `PopupOwner` from a `PublicUser` without leaking the full type.
 */
export function ownerFromUser(u: PublicUser | null | undefined): PopupOwner | null {
	if (!u) return null;
	return { displayName: u.displayName, email: u.email };
}
