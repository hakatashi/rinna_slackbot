import {LanguageServiceClient} from '@google-cloud/language';

/** Mirrors worker.py's classify_text: flags a message if Google's V2
 * content classification model puts it in the /Adult category. */
export class GoogleLanguageModerator {
	private readonly client = new LanguageServiceClient();

	async classifyText(text: string): Promise<{isAdult: boolean; raw: unknown}> {
		const [classification] = await this.client.classifyText({
			document: {
				content: text,
				type: 'PLAIN_TEXT',
				language: 'JA',
			},
			classificationModelOptions: {
				v2Model: {contentCategoriesVersion: 'V2'},
			},
		});

		const isAdult = (classification.categories ?? []).some(
			(category) => category.name === '/Adult',
		);
		return {isAdult, raw: classification};
	}
}
