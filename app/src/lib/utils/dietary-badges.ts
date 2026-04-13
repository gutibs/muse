import type { Tag } from '$lib/types';

const BADGE_MAP: Record<string, { label: string; icon: string; bg: string; color: string }> = {
	'kosher': { label: 'Kosher', icon: '✡', bg: '#EFF6FF', color: '#1D4ED8' },
	'sin-tacc': { label: 'Sin TACC', icon: '🌾', bg: '#FFFBEB', color: '#B45309' },
};

export function dietaryBadgesHtml(tags: Tag[] | undefined): string {
	if (!tags?.length) return '';
	const badges = tags
		.filter((t) => BADGE_MAP[t.slug])
		.map((t) => {
			const b = BADGE_MAP[t.slug];
			return `<span style="display:inline-flex;align-items:center;gap:2px;background:${b.bg};color:${b.color};font-size:10px;font-weight:500;padding:1px 6px;border-radius:9px;">${b.icon} ${b.label}</span>`;
		});
	if (!badges.length) return '';
	return `<br><div style="display:flex;gap:4px;margin-top:3px;">${badges.join('')}</div>`;
}
