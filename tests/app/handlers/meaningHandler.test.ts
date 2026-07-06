import {afterEach, beforeEach, describe, expect, it, vi} from 'vitest';
import {meaningHandler} from '../../../src/app/handlers/meaningHandler.js';
import {createFakeDeps} from '../fakeDeps.js';

beforeEach(() => {
	vi.useFakeTimers();
});

afterEach(() => {
	vi.useRealTimers();
});

describe('meaningHandler', () => {
	it('is a no-op for a persona without a meaningIntro configured', async () => {
		const {chatPoster, deps} = createFakeDeps();
		await meaningHandler({word: 'テスト', character: 'りんな'}, deps);
		expect(chatPoster.posts).toHaveLength(0);
	});

	it('prefixes the first chunk with "{word}っていうのは、" and posts under the decorated username', async () => {
		const {llm, chatPoster, deps} = createFakeDeps();
		llm.generateOutput = 'こういう意味だよ」';

		const promise = meaningHandler({word: 'テスト単語'}, deps);
		await vi.runAllTimersAsync();
		await promise;

		expect(chatPoster.posts).toHaveLength(1);
		expect(chatPoster.posts[0]?.text).toBe(
			'テスト単語っていうのは、こういう意味だよ',
		);
		expect(chatPoster.posts[0]?.username).toContain('今言うな');
		expect(chatPoster.posts[0]?.username).toContain(
			'おじさんが役に立たないときに助けてくれる',
		);
	});

	it('sleeps before posting even the very first chunk (unlike the persona-response flow)', async () => {
		const {llm, deps} = createFakeDeps();
		llm.generateOutput = 'こういう意味だよ」';
		const setTimeoutSpy = vi.spyOn(global, 'setTimeout');

		const promise = meaningHandler({word: 'テスト単語'}, deps);
		await vi.runAllTimersAsync();
		await promise;

		expect(setTimeoutSpy).toHaveBeenCalledTimes(1);
	});

	it('censors the posted text but keeps the logged outputSpeech uncensored', async () => {
		const {llm, chatPoster, moderator, responseLog, deps} = createFakeDeps();
		llm.generateOutput = 'やばい意味だよ」';
		moderator.censoredTexts.add('テスト単語っていうのは、やばい意味だよ');

		const promise = meaningHandler({word: 'テスト単語'}, deps);
		await vi.runAllTimersAsync();
		await promise;

		expect(chatPoster.posts[0]?.text).toBe('##### CENSORED #####');
		expect(responseLog.records[0]?.outputSpeech).toBe('やばい意味だよ');
	});

	it('passes threadTs to the Slack post but omits it from the response log record', async () => {
		const {llm, chatPoster, responseLog, deps} = createFakeDeps();
		llm.generateOutput = 'こういう意味だよ」';

		const promise = meaningHandler(
			{word: 'テスト単語', threadTs: '1234.5'},
			deps,
		);
		await vi.runAllTimersAsync();
		await promise;

		expect(chatPoster.posts[0]?.threadTs).toBe('1234.5');
		expect(responseLog.records[0]?.threadTs).toBeUndefined();
	});
});
