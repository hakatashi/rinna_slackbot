import type {AzureModerationTerm} from '../domain/dispatch/moderationRules.js';

export interface AzureContentModeratorOptions {
	readonly endpoint: string;
	readonly subscriptionKey: string;
}

interface AzureScreenResponse {
	Terms?: {Term: string}[];
}

/** Mirrors worker.py's screen_text call against Azure Content Moderator's
 * text_moderation.screen_text (autocorrect/PII/classify all disabled). */
export class AzureContentModerator {
	constructor(private readonly options: AzureContentModeratorOptions) {}

	async screenText(
		text: string,
	): Promise<{terms: AzureModerationTerm[] | null; raw: unknown}> {
		const url = `${this.options.endpoint}/contentmoderator/moderate/v1.0/ProcessText/Screen?autocorrect=false&PII=false&classify=false&language=jpn`;

		const response = await fetch(url, {
			method: 'POST',
			headers: {
				'Content-Type': 'text/plain; charset=UTF-8',
				'Ocp-Apim-Subscription-Key': this.options.subscriptionKey,
			},
			body: text,
		});

		if (!response.ok) {
			throw new Error(
				`Azure Content Moderator returned ${response.status}: ${await response.text()}`,
			);
		}

		const data = (await response.json()) as AzureScreenResponse;
		const terms = data.Terms?.map((term) => ({term: term.Term})) ?? null;
		return {terms, raw: data};
	}
}
