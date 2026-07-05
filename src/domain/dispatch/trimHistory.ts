import type {HumanMessage} from '../../contracts/pubsubPayloads.js';

const CLEAR_DIRECTIVES = /\/no_clear|\/clear/g;

export interface TrimHistoryResult {
	messages: HumanMessage[];
	triggerText: string;
}

/** Mirrors worker.py pubsub_callback's /clear and /no_clear handling: unless
 * /no_clear appears in the trigger (last) message, history is truncated to
 * start at the most recent message containing /clear. The directives
 * themselves are stripped from every message's text afterward. */
export function trimHistory(
	humanMessages: readonly HumanMessage[],
): TrimHistoryResult {
	const lastMessage = humanMessages.at(-1);
	const rawTriggerText = lastMessage?.text ?? '';

	const skipClear = rawTriggerText.includes('/no_clear');

	let lastClearIndex = -1;
	if (!skipClear) {
		humanMessages.forEach((msg, i) => {
			if (
				msg.text !== null &&
				msg.text !== undefined &&
				msg.text !== '' &&
				msg.text.includes('/clear')
			) {
				lastClearIndex = i;
			}
		});
	}

	const rawWindow =
		lastClearIndex >= 0 ? humanMessages.slice(lastClearIndex) : humanMessages;

	const messages = rawWindow.map((msg): HumanMessage => {
		if (msg.text === null || msg.text === undefined) return msg;
		return {...msg, text: msg.text.replace(CLEAR_DIRECTIVES, '').trim()};
	});

	const triggerText = rawTriggerText.replace(CLEAR_DIRECTIVES, '').trim();

	return {messages, triggerText};
}
