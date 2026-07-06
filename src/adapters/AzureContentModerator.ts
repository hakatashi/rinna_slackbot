import type {AzureModerationTerm} from '../domain/dispatch/moderationRules.js';

export interface AzureContentModeratorOptions {
	readonly endpoint: string;
	readonly subscriptionKey: string;
}

// The REST API's JSON body uses snake_case keys (terms/term/original_text/...),
// not the PascalCase the .NET-flavored docs might suggest — confirmed against
// a live response. This also happens to match what the sibling repo's `info`
// command reads (moderation.azure_content_moderator.terms), so `raw` is
// stored as-is rather than reshaped.
interface AzureScreenResponse {
	terms?: {term: string}[];
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
		const terms = data.terms?.map((term) => ({term: term.term})) ?? null;
		return {terms, raw: data};
	}
}
