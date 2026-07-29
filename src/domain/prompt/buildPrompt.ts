import type {HumanMessage} from '../../contracts/pubsubPayloads.js';
import {
	findPersonaByBotUsername,
	type PersonaId,
	personaMeta,
	RINNA_BOT_ID,
} from '../personas.js';
import {SENTENCE_DELIMITERS} from '../sentenceDelimiters.js';
import {type DialogueEntry, formatMessage} from './formatMessage.js';
import {normalizeText} from './normalizeInput.js';
import {
	substituteDatePlaceholders,
	substituteUserPlaceholders,
} from './placeholders.js';
import {getTopHumanUsernames} from './topHumanUsernames.js';

const MAX_PROMPT_TOKENS = 11500;
const MAX_HISTORY_TOKENS = 2000;

export interface PersonaPromptData {
	intro: string;
	inquiryIntro?: string;
	/** Unused by buildPrompt itself; carried here so persona data has one shape shared with the meaning flow. */
	meaningIntro?: string;
}

export interface BuildPromptResult {
	tokenIds: readonly number[] | null;
	textInput: string;
	formattedDialog: string;
}

export type Tokenize = (text: string) => Promise<readonly number[]>;

/** A trigger message ending in ？/? gets the "quick inquiry" prompt shape
 * (only the trigger message itself, no history). Exported so callers that
 * need to know this ahead of buildPrompt (e.g. deciding which messages'
 * image attachments are even in scope) can replicate the same rule. */
export function isInquiryText(text: string): boolean {
	return text.endsWith('？') || text.endsWith('?');
}

function resolveSpeakerName(
	message: HumanMessage,
	usernameMapping: Record<string, string>,
): string {
	if (message.bot_id === RINNA_BOT_ID && message.username !== undefined) {
		const persona = findPersonaByBotUsername(message.username);
		if (persona !== undefined) return persona.nameInText;
	}
	if (message.user !== undefined && message.user in usernameMapping) {
		return usernameMapping[message.user] as string;
	}
	return message.user ?? '';
}

function buildFormattedMessages(
	messages: readonly HumanMessage[],
	usernameMapping: Record<string, string>,
): DialogueEntry[] {
	const formatted: DialogueEntry[] = [];

	for (const message of messages) {
		if (message.text === null || message.text === undefined) continue;
		let messageText = message.text;

		const contextMatch = /^\((.+?)\).+$/.exec(messageText);
		if (contextMatch !== null) {
			const context = contextMatch[1] as string;
			formatted.push({text: normalizeText(context), user: 'context'});
			messageText = messageText.slice(messageText.indexOf(')') + 1).trim();
		}

		const text = normalizeText(messageText);
		if (text === '') continue;

		const user = resolveSpeakerName(message, usernameMapping);

		const last = formatted.at(-1);
		if (last !== undefined && last.user === user) {
			const lastChar = last.text.at(-1);
			if (
				last.text.length > 0 &&
				lastChar !== undefined &&
				SENTENCE_DELIMITERS.includes(lastChar)
			) {
				last.text = `${last.text} ${text}`;
			} else {
				last.text = `${last.text}。${text}`;
			}
		} else {
			formatted.push({text, user});
		}
	}

	return formatted;
}

/**
 * Mirrors rinna/generation.py _prepare_generation. Grows the included
 * history one message at a time (newest-first) until the token budget would
 * be exceeded, then returns the last window that still fit. Note: on the
 * failing iteration, textInput/formattedDialog are updated to the
 * over-budget candidate before returning (matching the original's info-only
 * quirk) while tokenIds stays at the last successful value.
 */
export async function buildPrompt(
	messages: readonly HumanMessage[],
	character: PersonaId,
	personaData: PersonaPromptData,
	usernameMapping: Record<string, string>,
	tokenize: Tokenize,
	now: Date,
	/** Appended right before the persona's speech-opening 「, e.g. image
	 * markers for attached images. Opaque to buildPrompt itself. */
	extraSuffix = '',
): Promise<BuildPromptResult> {
	const meta = personaMeta[character];
	const lastMessage = messages.at(-1);
	const lastMessageText = lastMessage?.text ?? '';
	const isInquiry = isInquiryText(lastMessageText);

	const [user1, user2] = getTopHumanUsernames(messages, usernameMapping);

	if (isInquiry && personaData.inquiryIntro !== undefined) {
		const inquiryIntro = substituteUserPlaceholders(
			personaData.inquiryIntro,
			user1,
			user2,
		);
		const formattedDialog = `質問「${lastMessageText}」`;
		const textInput = `${inquiryIntro}\n${formattedDialog}${extraSuffix}\n回答「`;
		const tokenIds = await tokenize(textInput);
		return {tokenIds, textInput, formattedDialog};
	}

	const formattedMessages = buildFormattedMessages(messages, usernameMapping);
	formattedMessages.reverse();

	const baseIntro = substituteUserPlaceholders(personaData.intro, user1, user2);
	const intro = `${baseIntro}\n`;
	const outro = `\n${meta.nameInText}「`;

	const baseText = substituteDatePlaceholders(`${intro}\n${outro}`, now);
	const baseLen = (await tokenize(baseText)).length;

	let tokenIdsOutput: readonly number[] | null = null;
	let textInput = '';
	let formattedDialog = '';
	const window: DialogueEntry[] = [];

	for (const message of formattedMessages) {
		window.unshift(message);
		formattedDialog = window.map(formatMessage).join('\n');
		const candidateText = substituteDatePlaceholders(
			`${intro}\n${formattedDialog}${extraSuffix}${outro}`,
			now,
		);

		const tokenIds = await tokenize(candidateText);
		const inputLen = tokenIds.length;
		const historyLen = inputLen - baseLen;

		textInput = candidateText;

		if (inputLen > MAX_PROMPT_TOKENS || historyLen > MAX_HISTORY_TOKENS) {
			break;
		}
		tokenIdsOutput = tokenIds;
	}

	return {tokenIds: tokenIdsOutput, textInput, formattedDialog};
}
