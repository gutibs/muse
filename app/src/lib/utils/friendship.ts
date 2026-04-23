import type { Friendship, PublicUser } from '$lib/types';

export function getOtherUser(f: Friendship, myId: number): PublicUser {
	return f.fromUser.id === myId ? f.toUser : f.fromUser;
}
