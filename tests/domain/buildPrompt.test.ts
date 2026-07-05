import {describe, expect, it} from 'vitest';
import type {HumanMessage} from '../../src/contracts/pubsubPayloads.js';
import {RINNA_BOT_ID} from '../../src/domain/personas.js';
import {buildPrompt} from '../../src/domain/prompt/buildPrompt.js';

/** A fake tokenizer: token count == character count, so budgets are easy to reason about. */
function fakeTokenize(text: string): Promise<readonly number[]> {
	return Promise.resolve(Array.from(text, (_, i) => i));
}

const usernameMapping = {U1: '博多市', U2: 'ひでお'};
const now = new Date(2026, 0, 5, 12, 0);

describe('buildPrompt', () => {
	it('formats a simple dialogue and appends the outro prompt', async () => {
		const messages: HumanMessage[] = [
			{text: 'こんにちは', user: 'U1', ts: '1'},
		];
		const result = await buildPrompt(
			messages,
			'りんな',
			{intro: 'イントロ'},
			usernameMapping,
			fakeTokenize,
			now,
		);
		expect(result.formattedDialog).toBe('博多市「こんにちは」');
		expect(result.textInput).toBe('イントロ\n\n博多市「こんにちは」\nりんな「');
		expect(result.tokenIds).not.toBeNull();
	});

	it('merges consecutive messages from the same speaker with 。', async () => {
		const messages: HumanMessage[] = [
			{text: 'やあ', user: 'U1', ts: '1'},
			{text: '元気?', user: 'U1', ts: '2'},
		];
		const result = await buildPrompt(
			messages,
			'りんな',
			{intro: 'イントロ'},
			usernameMapping,
			fakeTokenize,
			now,
		);
		expect(result.formattedDialog).toBe('博多市「やあ。元気?」');
	});

	it('merges with a space instead when the prior text already ends with a delimiter', async () => {
		const messages: HumanMessage[] = [
			{text: '元気？', user: 'U1', ts: '1'},
			{text: 'うん！', user: 'U1', ts: '2'},
		];
		const result = await buildPrompt(
			messages,
			'りんな',
			{intro: 'イントロ'},
			usernameMapping,
			fakeTokenize,
			now,
		);
		expect(result.formattedDialog).toBe('博多市「元気？ うん！」');
	});

	it('extracts a leading (context) annotation as its own context line', async () => {
		const messages: HumanMessage[] = [
			{text: '(晴れ)今日はいい天気だね', user: 'U1', ts: '1'},
		];
		const result = await buildPrompt(
			messages,
			'りんな',
			{intro: 'イントロ'},
			usernameMapping,
			fakeTokenize,
			now,
		);
		expect(result.formattedDialog).toBe('(晴れ)\n博多市「今日はいい天気だね」');
	});

	it('maps rinna-posted bot history back to persona display names', async () => {
		const messages: HumanMessage[] = [
			{text: 'こんにちは', user: 'U1', ts: '1'},
			{text: 'やあ', bot_id: RINNA_BOT_ID, username: '今言うな', ts: '2'},
		];
		const result = await buildPrompt(
			messages,
			'りんな',
			{intro: 'イントロ'},
			usernameMapping,
			fakeTokenize,
			now,
		);
		expect(result.formattedDialog).toBe('博多市「こんにちは」\nウナ「やあ」');
	});

	it('takes the inquiry branch for a question when inquiryIntro is configured', async () => {
		const messages: HumanMessage[] = [{text: '今何時？', user: 'U1', ts: '1'}];
		const result = await buildPrompt(
			messages,
			'りんな',
			{intro: 'イントロ', inquiryIntro: '質問イントロ'},
			usernameMapping,
			fakeTokenize,
			now,
		);
		expect(result.formattedDialog).toBe('質問「今何時？」');
		expect(result.textInput).toBe('質問イントロ\n質問「今何時？」\n回答「');
	});

	it('does not take the inquiry branch when no inquiryIntro is configured, even for a question', async () => {
		const messages: HumanMessage[] = [{text: '今何時？', user: 'U1', ts: '1'}];
		const result = await buildPrompt(
			messages,
			'りんな',
			{intro: 'イントロ'},
			usernameMapping,
			fakeTokenize,
			now,
		);
		expect(result.formattedDialog).toBe('博多市「今何時？」');
	});

	it('substitutes date placeholders using the injected clock', async () => {
		const messages: HumanMessage[] = [
			{text: 'こんにちは', user: 'U1', ts: '1'},
		];
		const result = await buildPrompt(
			messages,
			'りんな',
			{intro: '[MONTH]月[DATE]日 [WEEKDAY]曜日 [HOUR]時[MINUTE]分 [WEATHER]'},
			usernameMapping,
			fakeTokenize,
			now,
		);
		expect(
			result.textInput.startsWith('1月5日 月曜日 午前12時0分 くもり'),
		).toBe(true);
	});

	it('grows the history window backward until the token budget is exceeded, keeping the last window that fit', async () => {
		const messages: HumanMessage[] = [
			{
				text: 'old-message-that-is-long-enough-to-blow-the-budget',
				user: 'U1',
				ts: '1',
			},
			{text: 'newest', user: 'U2', ts: '2'},
		];
		// Any prompt longer than ~40 "tokens" (chars, per fakeTokenize) blows the budget hard.
		const tightTokenize = (text: string): Promise<readonly number[]> =>
			Promise.resolve(
				Array.from({length: text.length > 40 ? 99_999 : text.length}),
			);

		const result = await buildPrompt(
			messages,
			'りんな',
			{intro: 'イ'},
			usernameMapping,
			tightTokenize,
			now,
		);
		// Only the newest message should survive in the returned tokens...
		expect(result.tokenIds).not.toBeNull();
		expect(result.tokenIds?.length).toBeLessThan(99_999);
		// ...but formattedDialog/textInput reflect the failed (over-budget) last attempt, matching
		// the original Python's quirk of updating those before the break.
		expect(result.formattedDialog).toContain(
			'old-message-that-is-long-enough-to-blow-the-budget',
		);
	});

	it('returns null tokenIds when even the single newest message exceeds the budget', async () => {
		const messages: HumanMessage[] = [
			{text: 'x'.repeat(3000), user: 'U1', ts: '1'},
		];
		const result = await buildPrompt(
			messages,
			'りんな',
			{intro: 'イ'},
			usernameMapping,
			fakeTokenize,
			now,
		);
		expect(result.tokenIds).toBeNull();
	});
});
