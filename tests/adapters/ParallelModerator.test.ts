import {describe, expect, it} from 'vitest';
import {
	ParallelModerator,
	type TextClassifier,
	type TextScreener,
} from '../../src/adapters/ParallelModerator.js';

function classifier(isAdult: boolean): TextClassifier {
	return {classifyText: async () => ({isAdult, raw: {isAdult}})};
}

function screener(terms: {term: string}[] | null): TextScreener {
	return {screenText: async () => ({terms, raw: {terms}})};
}

describe('ParallelModerator', () => {
	it('does not censor when neither service flags the text', async () => {
		const moderator = new ParallelModerator(classifier(false), screener(null));
		const result = await moderator.moderate('こんにちは');
		expect(result.censored).toBe(false);
	});

	it('censors when Google flags adult content, even if Azure finds nothing', async () => {
		const moderator = new ParallelModerator(classifier(true), screener(null));
		const result = await moderator.moderate('x');
		expect(result.censored).toBe(true);
	});

	it('censors when Azure finds a non-allowlisted term, even if Google is clean', async () => {
		const moderator = new ParallelModerator(
			classifier(false),
			screener([{term: 'ng-word'}]),
		);
		const result = await moderator.moderate('x');
		expect(result.censored).toBe(true);
	});

	it('does not censor when Azure only finds allowlisted terms', async () => {
		const moderator = new ParallelModerator(
			classifier(false),
			screener([{term: 'えた'}]),
		);
		const result = await moderator.moderate('x');
		expect(result.censored).toBe(false);
	});

	it('carries both raw results through to details for logging', async () => {
		const moderator = new ParallelModerator(classifier(false), screener(null));
		const result = await moderator.moderate('x');
		expect(result.details.googleLanguageService).toEqual({isAdult: false});
		expect(result.details.azureContentModerator).toEqual({terms: null});
	});
});
