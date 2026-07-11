import {afterEach, beforeEach, describe, expect, it, vi} from 'vitest';
import {generateAndPostPersonaResponse} from '../../src/app/generatePersonaResponse.js';
import type {HumanMessage} from '../../src/contracts/pubsubPayloads.js';
import {createFakeDeps} from './fakeDeps.js';

const messages: HumanMessage[] = [
	{text: 'りんな、おはよう', user: 'U1', ts: '1'},
];

beforeEach(() => {
	vi.useFakeTimers();
});

afterEach(() => {
	vi.useRealTimers();
});

describe('generateAndPostPersonaResponse', () => {
	it('posts each streamed chunk and returns the joined speech', async () => {
		const {llm, chatPoster, deps} = createFakeDeps();
		llm.streamPieces = ['おはよう。', '元気？'];

		const promise = generateAndPostPersonaResponse(
			messages,
			'りんな',
			undefined,
			deps,
		);
		await vi.runAllTimersAsync();
		const result = await promise;

		expect(chatPoster.posts.map((p) => p.text)).toEqual(['おはよう', '元気？']);
		expect(result).toBe('おはよう。元気？');
	});

	it('does not sleep before the first chunk but does before subsequent ones', async () => {
		const {llm, deps} = createFakeDeps();
		llm.streamPieces = ['一。', '二。', '三。'];
		const setTimeoutSpy = vi.spyOn(global, 'setTimeout');

		const promise = generateAndPostPersonaResponse(
			messages,
			'りんな',
			undefined,
			deps,
		);
		await vi.runAllTimersAsync();
		await promise;

		// Only 2 sleeps for 3 chunks (none before the first).
		expect(setTimeoutSpy).toHaveBeenCalledTimes(2);
	});

	it('posts a censored placeholder but returns the original uncensored speech', async () => {
		const {llm, chatPoster, moderator, deps} = createFakeDeps();
		llm.streamPieces = ['やばい発言。'];
		moderator.censoredTexts.add('やばい発言');

		const promise = generateAndPostPersonaResponse(
			messages,
			'りんな',
			undefined,
			deps,
		);
		await vi.runAllTimersAsync();
		const result = await promise;

		expect(chatPoster.posts[0]?.text).toBe('##### CENSORED #####');
		expect(result).toBe('やばい発言');
	});

	it('passes threadTs through to both the Slack post and the response log', async () => {
		const {llm, chatPoster, responseLog, deps} = createFakeDeps();
		llm.streamPieces = ['おはよう。'];

		const promise = generateAndPostPersonaResponse(
			messages,
			'りんな',
			'12345.6789',
			deps,
		);
		await vi.runAllTimersAsync();
		await promise;

		expect(chatPoster.posts[0]?.threadTs).toBe('12345.6789');
		expect(responseLog.records[0]?.threadTs).toBe('12345.6789');
	});

	it('logs the full input message history alongside each posted chunk', async () => {
		const {llm, responseLog, deps} = createFakeDeps();
		llm.streamPieces = ['おはよう。'];

		const promise = generateAndPostPersonaResponse(
			messages,
			'りんな',
			undefined,
			deps,
		);
		await vi.runAllTimersAsync();
		await promise;

		expect(responseLog.records[0]?.inputMessages).toBe(messages);
		expect(responseLog.records[0]?.character).toBe('りんな');
	});

	it('returns an empty string and posts nothing when the token budget is exceeded for even the newest message', async () => {
		const {llm, chatPoster, deps} = createFakeDeps();
		// Force the budget to blow immediately by using a huge intro (tokenize = char count).
		deps.personaData['りんな'] = {intro: 'x'.repeat(20_000)};
		llm.streamPieces = ['should not be reached'];

		const result = await generateAndPostPersonaResponse(
			messages,
			'りんな',
			undefined,
			deps,
		);

		expect(result).toBe('');
		expect(chatPoster.posts).toHaveLength(0);
	});

	it('generates with promptText+images when images are provided, appending an image marker per image', async () => {
		const {llm, deps} = createFakeDeps();
		llm.streamPieces = ['はーい。'];

		const promise = generateAndPostPersonaResponse(
			messages,
			'りんな',
			undefined,
			deps,
			['base64img'],
		);
		await vi.runAllTimersAsync();
		await promise;

		const input = llm.receivedInputs[0];
		expect(input && 'promptText' in input).toBe(true);
		if (input && 'promptText' in input) {
			expect(input.images).toEqual(['base64img']);
			expect(input.promptText).toContain('<__media__>');
		}
	});

	it('uses the tokenIds path when no images are provided', async () => {
		const {llm, deps} = createFakeDeps();
		llm.streamPieces = ['はーい。'];

		const promise = generateAndPostPersonaResponse(
			messages,
			'りんな',
			undefined,
			deps,
		);
		await vi.runAllTimersAsync();
		await promise;

		const input = llm.receivedInputs[0];
		expect(input && 'tokenIds' in input).toBe(true);
	});
});
