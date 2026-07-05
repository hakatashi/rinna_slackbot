import {describe, expect, it} from 'vitest';
import {splitSpeechToChunks} from '../../src/domain/speech/splitChunks.js';

describe('splitSpeechToChunks', () => {
	it('splits on sentence delimiters', () => {
		expect(splitSpeechToChunks('おはよう。元気？うん！')).toEqual([
			'おはよう',
			'元気？',
			'うん！',
		]);
	});

	it('treats a run of consecutive delimiters as a single boundary', () => {
		expect(splitSpeechToChunks('えっ！？そうなの。')).toEqual([
			'えっ！？',
			'そうなの',
		]);
	});

	it('does not split while inside a bracket', () => {
		expect(splitSpeechToChunks('これは「疑問？」ですよ。')).toEqual([
			'これは「疑問？」ですよ',
		]);
	});

	it('keeps a trailing fragment with no delimiter as its own chunk', () => {
		expect(splitSpeechToChunks('おはよう。まだ話し中')).toEqual([
			'おはよう',
			'まだ話し中',
		]);
	});

	it('strips a single trailing 。but keeps an ellipsis-like run', () => {
		expect(splitSpeechToChunks('えっと……。')).toEqual(['えっと……']);
	});
});
