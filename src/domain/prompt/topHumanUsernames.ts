import type {HumanMessage} from '../../contracts/pubsubPayloads.js';

/** Mirrors rinna/generation.py get_top2_human_usernames: the two most
 * recent distinct human speakers, scanning newest-to-oldest. If only one
 * human is found, user2 falls back to the same name as user1. */
export function getTopHumanUsernames(
	messages: readonly HumanMessage[],
	usernameMapping: Record<string, string>,
): readonly [string | null, string | null] {
	const seen: string[] = [];

	for (const message of [...messages].reverse()) {
		if (message.bot_id !== undefined) continue;
		const userId = message.user;
		if (
			userId !== undefined &&
			userId !== 'context' &&
			!seen.includes(userId)
		) {
			seen.push(userId);
		}
		if (seen.length >= 2) break;
	}

	const names = seen.map((uid) => usernameMapping[uid] ?? uid);
	const user1 = names[0] ?? null;
	const user2 = names[1] ?? names[0] ?? null;
	return [user1, user2];
}
