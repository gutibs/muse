import type { Pin } from './pin';
import type { AnonymousUser } from './user';

export type ActivityVerb = 'pinned' | 'rated' | 'updated' | 'joined' | 'friendship';

export interface Activity {
	id: number;
	actor: AnonymousUser;
	verb: ActivityVerb;
	pin: Pin | null;
	targetUser: AnonymousUser | null;
	createdAt: string;
}
