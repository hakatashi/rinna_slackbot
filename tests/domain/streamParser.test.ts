import {describe, expect, it} from 'vitest';
import {streamSpeechChunks} from '../../src/domain/speech/streamParser.js';

async function* asAsyncIterable(
	pieces: readonly string[],
): AsyncGenerator<string, void, undefined> {
	for (const piece of pieces) {
		yield piece;
	}
}

async function collect(
	pieces: readonly string[],
	character: 'りんな' = 'りんな',
) {
	const out: string[] = [];
	for await (const chunk of streamSpeechChunks(
		asAsyncIterable(pieces),
		character,
	)) {
		out.push(chunk);
	}
	return out;
}

describe('streamSpeechChunks', () => {
	it('yields a chunk as soon as a sentence delimiter is confirmed', async () => {
		expect(await collect(['おはよう。', 'まだ話し中'])).toEqual([
			'おはよう',
			'まだ話し中',
		]);
	});

	it('does not split mid-run of consecutive delimiters even across piece boundaries', async () => {
		expect(await collect(['えっ！', '？そうなの。'])).toEqual([
			'えっ！？',
			'そうなの',
		]);
	});

	it('does not split on a delimiter that is inside brackets', async () => {
		expect(await collect(['これは「疑問？', '」ですよ。'])).toEqual([
			'これは「疑問？」ですよ',
		]);
	});

	it('applies persona replacements to each yielded chunk', async () => {
		expect(await collect(['ウナが来た。'])).toEqual(['うなが来た']);
	});

	it('flushes a trailing fragment with no terminating delimiter', async () => {
		expect(await collect(['続きがある'])).toEqual(['続きがある']);
	});
});
