import type { Pin } from './pin';
import type { AnonymousUser, PublicUser } from './user';

export type ActivityVerb = 'pinned' | 'rated' | 'updated' | 'joined' | 'friendship';

export interface Activity {
	id: number;
	actor: PublicUser;
	verb: ActivityVerb;
	pin: Pin | null;
	targetUser: AnonymousUser | null;
	createdAt: string;
}
