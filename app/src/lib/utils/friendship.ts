import type { AnonymousUser, Friendship } from '$lib/types';

/** La contraparte de una amistad. Sin email: el backend no lo entrega para
 * nadie que no seas vos. */
export function getOtherUser(f: Friendship, myId: number): AnonymousUser {
	return f.fromUser.id === myId ? f.toUser : f.fromUser;
}
