import {afterEach, beforeEach, describe, expect, it, vi} from 'vitest';
import {signalHandler} from '../../../src/app/handlers/signalHandler.js';
import type {RinnaSignalPayload} from '../../../src/contracts/pubsubPayloads.js';
import {createFakeDeps} from '../fakeDeps.js';

const NOW = new Date(2026, 0, 5, 12, 0); // epoch seconds ~ well beyond any test ts below

beforeEach(() => {
	vi.useFakeTimers();
});

afterEach(() => {
	vi.useRealTimers();
});

function signal(
	humanMessages: RinnaSignalPayload['humanMessages'],
): RinnaSignalPayload {
	return {type: 'rinna-signal', humanMessages};
}

describe('signalHandler', () => {
	it('fires only the mentioned persona for a single mention', async () => {
		const {llm, chatPoster, deps} = createFakeDeps(NOW);
		llm.streamPieces = ['はーい。'];

		const promise = signalHandler(
			signal([
				{
					text: 'りんな、こんにちは',
					user: 'U1',
					ts: String(NOW.getTime() / 1000),
				},
			]),
			deps,
		);
		await vi.runAllTimersAsync();
		await promise;

		expect(chatPoster.posts).toHaveLength(1);
		expect(chatPoster.posts[0]?.username).toBe('りんな');
	});

	it("fires multiple mentioned personas in order, each seeing the prior ones' replies", async () => {
		const {llm, chatPoster, deps} = createFakeDeps(NOW);
		// Every call to streamGenerate returns the same canned reply for simplicity;
		// what we're checking is the number/order/identity of personas triggered.
		llm.streamPieces = ['はーい。'];

		const promise = signalHandler(
			signal([
				{
					text: 'うのとりんなを呼んで',
					user: 'U1',
					ts: String(NOW.getTime() / 1000),
				},
			]),
			deps,
		);
		await vi.runAllTimersAsync();
		await promise;

		// detectTriggeredPersonas checks in fixed order りんな→うな→うか→うの→たたも,
		// regardless of mention order in the text.
		expect(chatPoster.posts.map((p) => p.username)).toEqual([
			'りんな',
			'皿洗うの',
		]);
	});

	it('falls back to a single random persona chosen from a pool excluding たたも when no name is mentioned', async () => {
		const {llm, chatPoster, deps: baseDeps} = createFakeDeps(NOW);
		llm.streamPieces = ['はーい。'];
		const seenPools: unknown[] = [];
		const deps = {
			...baseDeps,
			random: {
				choice: <T>(items: readonly T[]): T => {
					seenPools.push(items);
					return items[0] as T;
				},
			},
		};

		const promise = signalHandler(
			signal([
				{text: 'なんでもない話', user: 'U1', ts: String(NOW.getTime() / 1000)},
			]),
			deps,
		);
		await vi.runAllTimersAsync();
		await promise;

		expect(chatPoster.posts).toHaveLength(1);
		expect(seenPools).toEqual([['りんな', 'うな', 'うか', 'うの']]);
	});

	it('does not set a thread_ts for a recent trigger message', async () => {
		const {llm, chatPoster, deps} = createFakeDeps(NOW);
		llm.streamPieces = ['はーい。'];

		const promise = signalHandler(
			signal([
				{
					text: 'りんな、こんにちは',
					user: 'U1',
					ts: String(NOW.getTime() / 1000),
				},
			]),
			deps,
		);
		await vi.runAllTimersAsync();
		await promise;

		expect(chatPoster.posts[0]?.threadTs).toBeUndefined();
	});

	it('replies in-thread when the trigger message is more than 15 minutes old', async () => {
		const {llm, chatPoster, deps} = createFakeDeps(NOW);
		llm.streamPieces = ['はーい。'];
		const oldTs = NOW.getTime() / 1000 - 20 * 60;

		const promise = signalHandler(
			signal([{text: 'りんな、こんにちは', user: 'U1', ts: String(oldTs)}]),
			deps,
		);
		await vi.runAllTimersAsync();
		await promise;

		expect(chatPoster.posts[0]?.threadTs).toBe(String(oldTs));
	});

	it('routes @うな先生 mentions to the meaning flow instead of any persona reply', async () => {
		const {llm, chatPoster, deps} = createFakeDeps(NOW);
		llm.generateOutput = 'こういう意味だよ」';

		const promise = signalHandler(
			signal([
				{
					text: '@うな先生 テスト単語',
					user: 'U1',
					ts: String(NOW.getTime() / 1000),
				},
			]),
			deps,
		);
		await vi.runAllTimersAsync();
		await promise;

		expect(chatPoster.posts).toHaveLength(1);
		expect(chatPoster.posts[0]?.username).toContain(
			'おじさんが役に立たないときに助けてくれる今言うな',
		);
	});

	it('truncates history at the most recent /clear before detecting personas', async () => {
		const {llm, chatPoster, deps} = createFakeDeps(NOW);
		llm.streamPieces = ['はーい。'];

		const promise = signalHandler(
			signal([
				{text: 'りんな、無視されるべき', user: 'U1', ts: '1'},
				{
					text: '/clear うな、呼んだ',
					user: 'U1',
					ts: String(NOW.getTime() / 1000),
				},
			]),
			deps,
		);
		await vi.runAllTimersAsync();
		await promise;

		expect(chatPoster.posts.map((p) => p.username)).toEqual(['今言うな']);
	});

	it('is a no-op when humanMessages is empty', async () => {
		const {chatPoster, deps} = createFakeDeps(NOW);
		await signalHandler(signal([]), deps);
		expect(chatPoster.posts).toHaveLength(0);
	});

	it('downloads an attached image and generates with promptText+images', async () => {
		const {llm, imageDownloader, deps} = createFakeDeps(NOW);
		llm.streamPieces = ['はーい。'];

		const promise = signalHandler(
			signal([
				{
					text: 'りんな、これ見て',
					user: 'U1',
					ts: String(NOW.getTime() / 1000),
					files: [
						{url_private: 'https://slack/img.png', mimetype: 'image/png'},
					],
				},
			]),
			deps,
		);
		await vi.runAllTimersAsync();
		await promise;

		expect(imageDownloader.downloadedUrls).toEqual(['https://slack/img.png']);
		const input = llm.receivedInputs[0];
		expect(input && 'promptText' in input).toBe(true);
		if (input && 'promptText' in input) {
			expect(input.images).toEqual(['base64(https://slack/img.png)']);
			expect(input.promptText).toContain('<__media__>');
		}
	});

	it('ignores non-image attachments', async () => {
		const {llm, imageDownloader, deps} = createFakeDeps(NOW);
		llm.streamPieces = ['はーい。'];

		const promise = signalHandler(
			signal([
				{
					text: 'りんな、これ見て',
					user: 'U1',
					ts: String(NOW.getTime() / 1000),
					files: [
						{url_private: 'https://slack/doc.pdf', mimetype: 'application/pdf'},
					],
				},
			]),
			deps,
		);
		await vi.runAllTimersAsync();
		await promise;

		expect(imageDownloader.downloadedUrls).toHaveLength(0);
		const input = llm.receivedInputs[0];
		expect(input && 'tokenIds' in input).toBe(true);
	});

	it('keeps only the 3 most recent images across the history window', async () => {
		const {imageDownloader, llm, deps} = createFakeDeps(NOW);
		llm.streamPieces = ['はーい。'];
		const baseTs = NOW.getTime() / 1000;

		const promise = signalHandler(
			signal([
				{
					text: '1枚目',
					user: 'U1',
					ts: String(baseTs - 30),
					files: [{url_private: 'https://slack/1.png', mimetype: 'image/png'}],
				},
				{
					text: '2枚目',
					user: 'U1',
					ts: String(baseTs - 20),
					files: [{url_private: 'https://slack/2.png', mimetype: 'image/png'}],
				},
				{
					text: '3枚目',
					user: 'U1',
					ts: String(baseTs - 10),
					files: [{url_private: 'https://slack/3.png', mimetype: 'image/png'}],
				},
				{
					text: 'りんな、4枚目',
					user: 'U1',
					ts: String(baseTs),
					files: [{url_private: 'https://slack/4.png', mimetype: 'image/png'}],
				},
			]),
			deps,
		);
		await vi.runAllTimersAsync();
		await promise;

		expect(imageDownloader.downloadedUrls).toEqual([
			'https://slack/2.png',
			'https://slack/3.png',
			'https://slack/4.png',
		]);
	});
});
