import type {HumanMessage} from '../contracts/pubsubPayloads.js';
import {type PersonaId, personaMeta} from '../domain/personas.js';
import {buildPrompt} from '../domain/prompt/buildPrompt.js';
import {IMAGE_MEDIA_MARKER} from '../domain/prompt/imageAttachments.js';
import {SENTENCE_DELIMITERS} from '../domain/sentenceDelimiters.js';
import {joinChunksToSpeech} from '../domain/speech/normalizeChunk.js';
import {streamSpeechChunks} from '../domain/speech/streamParser.js';
import type {AppDependencies} from './deps.js';

function sleep(ms: number): Promise<void> {
	return new Promise((resolve) => {
		setTimeout(resolve, ms);
	});
}

interface GenerationInfo {
	readonly textInput: string;
	readonly formattedDialog: string;
	readonly inputLen: number;
	readonly config: {modelProvider: string; modelName: string};
	output: string;
}

async function postChunk(
	message: string,
	character: PersonaId,
	messages: readonly HumanMessage[],
	info: GenerationInfo,
	threadTs: string | undefined,
	deps: AppDependencies,
): Promise<void> {
	const moderation = await deps.moderator.moderate(message);
	const textToPost = moderation.censored ? '##### CENSORED #####' : message;
	const meta = personaMeta[character];

	const posted = await deps.chatPoster.post({
		text: textToPost,
		channel: deps.sandboxChannel,
		iconUrl: meta.slackUserIcon,
		username: meta.slackUserName,
		...(threadTs !== undefined ? {threadTs} : {}),
	});

	await deps.responseLog.log({
		createdAt: deps.clock.now(),
		character,
		inputMessages: messages,
		inputText: info.textInput,
		inputDialog: info.formattedDialog,
		inputTokenLength: info.inputLen,
		output: info.output,
		outputSpeech: info.output,
		config: info.config,
		message: posted,
		moderations: {
			google_language_service: moderation.details.googleLanguageService,
			azure_content_moderator: moderation.details.azureContentModerator,
		},
		...(threadTs !== undefined ? {threadTs} : {}),
	});
}

/**
 * Mirrors worker.py's rinna_response (streaming path) + _post_rinna_chunk:
 * builds the prompt, streams sentence chunks from the LLM, posts each to
 * Slack (moderated) with a 1s delay between chunks (but not before the
 * first), logs each posted chunk to Firestore, and returns the joined full
 * speech — used as the synthesized bot-history entry when more personas
 * are triggered by the same message.
 */
export async function generateAndPostPersonaResponse(
	messages: readonly HumanMessage[],
	character: PersonaId,
	threadTs: string | undefined,
	deps: AppDependencies,
	images: readonly string[] = [],
): Promise<string> {
	const personaData = deps.personaData[character];
	const extraSuffix =
		images.length > 0 ? IMAGE_MEDIA_MARKER.repeat(images.length) : '';
	const {tokenIds, textInput, formattedDialog} = await buildPrompt(
		messages,
		character,
		personaData,
		deps.usernameMapping,
		(text) => deps.llm.tokenize(text),
		deps.clock.now(),
		extraSuffix,
	);

	if (tokenIds === null) return '';

	const info: GenerationInfo = {
		textInput,
		formattedDialog,
		inputLen: tokenIds.length,
		config: deps.llm.describe(),
		output: '',
	};

	const allChunks: string[] = [];
	let firstChunk = true;

	const generateInput =
		images.length > 0 ? {promptText: textInput, images} : {tokenIds};

	for await (const chunk of streamSpeechChunks(
		deps.llm.streamGenerate(generateInput),
		character,
	)) {
		if (chunk.length === 0) continue;

		if (!firstChunk) await sleep(1000);
		firstChunk = false;

		if (info.output.length > 0) {
			const lastChar = info.output.at(-1) as string;
			info.output += SENTENCE_DELIMITERS.includes(lastChar) ? ' ' : '。';
		}
		info.output += chunk;

		await postChunk(chunk, character, messages, info, threadTs, deps);
		allChunks.push(chunk);
	}

	return joinChunksToSpeech(allChunks);
}
