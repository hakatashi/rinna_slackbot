import type {
	HumanMessage,
	RinnaSignalPayload,
} from '../../contracts/pubsubPayloads.js';
import {
	detectTriggeredPersonas,
	pickFallbackPersona,
} from '../../domain/dispatch/detectPersonas.js';
import {trimHistory} from '../../domain/dispatch/trimHistory.js';
import {personaMeta, RINNA_BOT_ID} from '../../domain/personas.js';
import {selectRecentImageUrls} from '../../domain/prompt/imageAttachments.js';
import {getTopHumanUsernames} from '../../domain/prompt/topHumanUsernames.js';
import type {AppDependencies} from '../deps.js';
import {generateAndPostPersonaResponse} from '../generatePersonaResponse.js';
import {meaningHandler} from './meaningHandler.js';

const THREAD_REPLY_THRESHOLD_SECONDS = 15 * 60;

/**
 * Mirrors worker.py's pubsub_callback rinna-signal branch: computes
 * thread-reply behavior for stale triggers, applies /clear and /no_clear,
 * then either routes to the @うな先生 meaning flow or fires each mentioned
 * persona in turn — appending each one's reply to the running history
 * before generating the next, so a message naming multiple personas has
 * them "see" each other's replies.
 */
export async function signalHandler(
	payload: RinnaSignalPayload,
	deps: AppDependencies,
): Promise<void> {
	const triggerMessage = payload.humanMessages.at(-1);
	if (triggerMessage === undefined) return;

	const triggerTs = Number.parseFloat(triggerMessage.ts);
	const nowTsSeconds = deps.clock.now().getTime() / 1000;
	const threadTs =
		nowTsSeconds - triggerTs > THREAD_REPLY_THRESHOLD_SECONDS
			? triggerMessage.ts
			: undefined;

	const {messages: trimmedMessages, triggerText} = trimHistory(
		payload.humanMessages,
	);

	if (triggerText.includes('@うな先生')) {
		const word = triggerText.replace(/^@うな先生/, '').trim();
		const [user1, user2] = getTopHumanUsernames(
			trimmedMessages,
			deps.usernameMapping,
		);
		await meaningHandler({word, character: 'うな', user1, user2}, deps);
		return;
	}

	const imageUrls = selectRecentImageUrls(
		trimmedMessages,
		deps.maxRecentImages,
	);
	const images = await Promise.all(
		imageUrls.map((url) => deps.imageDownloader.downloadBase64(url)),
	);

	let messages: readonly HumanMessage[] = trimmedMessages;
	const triggeredPersonas = detectTriggeredPersonas(triggerText);

	if (triggeredPersonas.length > 0) {
		for (const persona of triggeredPersonas) {
			const response = await generateAndPostPersonaResponse(
				messages,
				persona,
				threadTs,
				deps,
				images,
			);
			messages = [
				...messages,
				{
					bot_id: RINNA_BOT_ID,
					username: personaMeta[persona].slackUserName,
					text: response,
					// ts is never read on synthesized in-memory history entries
					// within this same invocation; kept only to satisfy the shape.
					ts: triggerMessage.ts,
				},
			];
		}
	} else {
		const fallback = pickFallbackPersona(triggerText, deps.random);
		await generateAndPostPersonaResponse(
			messages,
			fallback,
			threadTs,
			deps,
			images,
		);
	}
}
