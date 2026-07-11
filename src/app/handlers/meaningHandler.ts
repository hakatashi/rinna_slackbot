import {type PersonaId, personaMeta} from '../../domain/personas.js';
import {substituteUserPlaceholders} from '../../domain/prompt/placeholders.js';
import {applyRinnaReplacements} from '../../domain/speech/applyReplacements.js';
import {splitSpeechToChunks} from '../../domain/speech/splitChunks.js';
import type {AppDependencies} from '../deps.js';

function sleep(ms: number): Promise<void> {
	return new Promise((resolve) => {
		setTimeout(resolve, ms);
	});
}

export interface MeaningRequest {
	readonly word: string;
	readonly threadTs?: string;
	readonly character?: PersonaId;
	readonly user1?: string | null;
	readonly user2?: string | null;
}

/**
 * Mirrors rinna/generation.py generate_rinna_meaning combined with
 * worker.py's rinna_meaning: the "@うな先生, explain a word" flow. A no-op
 * for personas without a meaningIntro configured (only うな has one).
 * Unlike the persona-response flow, this always sleeps 1s before posting
 * every chunk, including the first.
 */
export async function meaningHandler(
	request: MeaningRequest,
	deps: AppDependencies,
): Promise<void> {
	const character = request.character ?? 'うな';
	const personaData = deps.personaData[character];
	if (personaData.meaningIntro === undefined) return;

	const meta = personaMeta[character];
	const user1 = request.user1 ?? null;
	const user2 = request.user2 ?? null;

	const meaningIntro = substituteUserPlaceholders(
		personaData.meaningIntro,
		user1,
		user2,
	);
	const inquiryName = user2 ?? 'ひでお';
	const inquiryMessage = `${inquiryName}「${meta.nameInText}、『${request.word}』ってわかる？」`;
	const responseMessage = `${meta.nameInText}「『${request.word}』っていうのは、`;
	const textInput = `${meaningIntro}\n${inquiryMessage}\n${responseMessage}`;

	const tokenIds = await deps.llm.tokenize(textInput);
	const {output} = await deps.llm.generate({tokenIds});

	const rawSpeech = output.split('」')[0] ?? '';
	const rinnaSpeech = applyRinnaReplacements(rawSpeech, character);
	const speechChunks = splitSpeechToChunks(rinnaSpeech);

	const config: Record<string, unknown> = {...deps.llm.describe()};
	const inputLen = tokenIds.length;

	for (let i = 0; i < speechChunks.length; i++) {
		let message = speechChunks[i] as string;
		if (message.length === 0) continue;
		if (i === 0) message = `${request.word}っていうのは、${message}`;

		await sleep(1000);

		const moderation = await deps.moderator.moderate(message);
		const textToPost = moderation.censored ? '##### CENSORED #####' : message;

		const posted = await deps.chatPoster.post({
			text: textToPost,
			channel: deps.sandboxChannel,
			iconUrl: meta.slackUserIcon,
			username: `おじさんが役に立たないときに助けてくれる${meta.slackUserName}`,
			...(request.threadTs !== undefined ? {threadTs: request.threadTs} : {}),
		});

		await deps.responseLog.log({
			createdAt: deps.clock.now(),
			character,
			inputMessages: [],
			inputText: textInput,
			inputDialog: '',
			inputTokenLength: inputLen,
			output,
			outputSpeech: rinnaSpeech,
			config,
			message: posted,
			moderations: {
				google_language_service: moderation.details.googleLanguageService,
				azure_content_moderator: moderation.details.azureContentModerator,
			},
		});
	}
}
