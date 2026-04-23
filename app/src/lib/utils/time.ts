/**
 * Short relative-time formatter shared across feed, home and restaurant pages.
 * Uses concise "Xm / Xh / Xd" labels; falls back to a short ISO date beyond a week.
 */
export function timeAgo(iso: string | null | undefined): string {
	if (!iso) return '';
	const d = new Date(iso);
	const diff = Date.now() - d.getTime();
	if (Number.isNaN(diff)) return '';

	const mins = Math.floor(diff / 60000);
	if (mins < 1) return 'just now';
	if (mins < 60) return `${mins}m`;

	const hours = Math.floor(mins / 60);
	if (hours < 24) return `${hours}h`;

	const days = Math.floor(hours / 24);
	if (days < 7) return `${days}d`;

	return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
}
