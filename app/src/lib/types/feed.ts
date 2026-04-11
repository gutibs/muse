import type { Pin } from './pin';
import type { PublicUser } from './user';

export type ActivityVerb = 'pinned' | 'rated' | 'updated' | 'joined' | 'friendship';

export interface Activity {
	id: number;
	actor: PublicUser;
	verb: ActivityVerb;
	pin: Pin | null;
	targetUser: PublicUser | null;
	createdAt: string;
}
