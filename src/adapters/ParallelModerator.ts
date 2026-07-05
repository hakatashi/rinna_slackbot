import type {AzureModerationTerm} from '../domain/dispatch/moderationRules.js';
import {hasOffensiveTerm} from '../domain/dispatch/moderationRules.js';
import type {ModerationResult, Moderator} from '../ports/Moderator.js';

export interface TextClassifier {
	classifyText(text: string): Promise<{isAdult: boolean; raw: unknown}>;
}

export interface TextScreener {
	screenText(
		text: string,
	): Promise<{terms: AzureModerationTerm[] | null; raw: unknown}>;
}

/** Mirrors worker.py's moderate_message: runs Google Language and Azure
 * Content Moderator concurrently and censors if either flags the text.
 * Depends on the narrow TextClassifier/TextScreener shapes (rather than the
 * concrete adapter classes) so it can be unit tested without real
 * credentials. */
export class ParallelModerator implements Moderator {
	constructor(
		private readonly google: TextClassifier,
		private readonly azure: TextScreener,
	) {}

	async moderate(text: string): Promise<ModerationResult> {
		const [{isAdult, raw: googleRaw}, {terms, raw: azureRaw}] =
			await Promise.all([
				this.google.classifyText(text),
				this.azure.screenText(text),
			]);

		const isOffensive = hasOffensiveTerm(terms);

		return {
			censored: isAdult || isOffensive,
			details: {
				googleLanguageService: googleRaw,
				azureContentModerator: azureRaw,
			},
		};
	}
}
